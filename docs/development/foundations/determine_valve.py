from json import loads, JSONDecodeError

DEGREE = 360


class Stator:
    def __init__(self, positions=None, port_degrees=None, central_port=True):
        if positions is not None:
            self.stator = self.create_symmetric_stator(positions, central_port)
        elif port_degrees is not None:
            self.stator = self.create_asymmetric_stator(port_degrees, central_port)
        else:
            raise ValueError("Either positions or port_degrees must be provided.")

    def create_symmetric_stator(self, positions, central_port):
        """Creates a symmetric stator with evenly distributed ports."""
        stator_ = [None] * DEGREE
        degree_interval = int(DEGREE / positions)
        for i in range(positions):
            stator_ = self.replace_element(stator_, i * degree_interval, i + 1)
        stator_ = [stator_, []]
        if central_port:
            stator_[1].append(0)
        return stator_

    def create_asymmetric_stator(self, port_degrees, central_port):
        """Creates an asymmetric stator based on specified port degrees."""
        stator_ = [None] * DEGREE
        for index, degree in enumerate(port_degrees):
            stator_ = self.replace_element(stator_, degree, index + 1)
        stator_ = [stator_, []]
        if central_port:
            stator_[1].append(0)
        return stator_

    @staticmethod
    def replace_element(list_, index, value):
        """Replace an element at a given index in a list."""
        if index < 0 or index >= len(list_):
            raise IndexError("Index out of range.")
        list_[index] = value
        return list_

    def __str__(self):
        return str([(x, y) for x, y in enumerate(self.stator[0]) if y is not None]) + " " + str(self.stator[1])


class Rotor:
    def __init__(self, routes=None, connections=None, stator=None, central_port=True):
        if routes is not None:
            self.rotor = self.create_rotor_from_tec(routes, stator, central_port)
        elif connections is not None:
            self.rotor = self.create_rotor_from_pos(connections, stator)
        else:
            raise ValueError("Either routes or connections must be provided.")

    def create_rotor_from_tec(self, routes, stator, central_port):
        """Creates a rotor based on technical drawing routes."""
        rotor_ = [[None] * DEGREE, []]
        start_value = len([x for x in stator.stator[0] if x is not None]) + 1

        for route in routes:
            for degree in route:
                if degree == -1:
                    if central_port:
                        rotor_[1].append(start_value)
                    else:
                        raise ValueError("Central port not allowed.")
                else:
                    rotor_[0] = Stator.replace_element(rotor_[0], degree, start_value)
            start_value += 1
        assert len(rotor_[1]) <= 1
        return rotor_

    def create_rotor_from_pos(self, connections, stator):
        """Creates a rotor based on specified connections."""
        normalized_rotor = []
        if isinstance(connections, str):
            connections = loads(connections)
        stator_positions = len([x for x in stator.stator[0] if x is not None]) + 1
        for degree, connections_ in connections.items():
            current_rotor = [[None] * DEGREE, []]
            for connection in connections_:
                for port in connection:
                    if port != 0:
                        current_index = stator.stator[0].index(port)
                        current_rotor[0] = Stator.replace_element(current_rotor[0], current_index, stator_positions)
                    else:
                        current_rotor[1].append(stator_positions)
                stator_positions += 1
            stator_positions += 1
            normalized_rotor.append(self.turn_rotor(current_rotor, int(degree)))

        radial = self._add_incomplete_rotor_positions([i[0] for i in normalized_rotor])
        central_ = sorted([i[1] for i in normalized_rotor if len(i[1]) > 0])[0]
        return [radial, central_]

    def turn_rotor(self, rotor_, degrees_):
        """Rotate the rotor by a given number of degrees."""
        if len(rotor_[0]) != 360:
            raise ValueError("Rotor length must be 360.")
        return [rotor_[0][degrees_:] + rotor_[0][:degrees_], rotor_[1]]

    def _add_incomplete_rotor_positions(self, rotor_positions):
        """Adds incomplete rotor positions by summing None values."""

        def sum_none(elements):
            for x in sorted([y for y in elements if y is not None]):
                if x is not None:
                    return x

        return [sum_none(elements) for elements in zip(*rotor_positions)]

    def __str__(self):
        return str(self.rotor)


def shorten_valve(stator, rotor):
    """Shortens the valve by removing unnecessary None values."""
    port_steps = []
    distance = 360
    for x, y in enumerate(stator.stator[0]):
        if y is not None:
            port_steps.append(x)
    for current, next_ in zip(port_steps, port_steps[1:] + port_steps[:1]):
        if next_ > current:
            distance = next_ - current if next_ - current < distance else distance
        else:
            distance = (DEGREE - current + next_) if DEGREE - current + next_ < distance else distance
    return [stator.stator[0][::distance], stator.stator[1]], [rotor.rotor[0][::distance], rotor.rotor[1]]


def main():
    """Main function to run the valve configuration."""
    try:
        msg = ("Before using this script, it is recommended that the user read the documentation about valve logic \n"
               "to become familiar with the terms: stator, routes, rotor, and symmetric. With this in mind, \n"
               "let's continue. Is your stator symmetric? Type yes or no: ")
        sym = input(msg).lower()
        central = input("Is there a central port on your valve? Type yes or no: ").lower()
        central = central == "yes"

        if sym == "yes":
            number = int(input("How many ports do you have radially distributed? Please give a number like 5: "))
            stator = Stator(positions=number, central_port=central)
        elif sym == "no":
            degrees = loads(input("Please provide a list of ports by their degree, e.g., [120, 200, 280]: "))
            stator = Stator(port_degrees=degrees, central_port=central)
        else:
            raise ValueError("Invalid input for symmetry.")

        print("Stator Configuration:", stator)

        rotor_input = input("Do you want to create the rotor from a technical drawing? Type yes or no: ").lower()
        if rotor_input == "yes":
            routes = loads(input("Please provide routes lists, e.g., [[120,200,-1]]: "))
            rotor = Rotor(routes=routes, stator=stator, central_port=central)
        elif rotor_input == "no":
            conns = input('Provide a mapping of degrees to ports connecting at this value. Format: {"0":[[0,1]]}: ')
            rotor = Rotor(connections=conns, stator=stator)
        else:
            raise ValueError("Invalid input for rotor creation.")

        stator, rotor = shorten_valve(stator, rotor)
        print("Rotor Configuration:", rotor)

    except (ValueError, JSONDecodeError, IndexError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
