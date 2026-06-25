import requests

OK = 200
NOT_FOUND = 404


def test_read_main(flowchem_test_instance):
    response = requests.get(r"http://127.0.0.1:8000/", timeout=5)
    assert response.status_code == OK
    assert "Flowchem" in response.text

    response = requests.get(
        r"http://127.0.0.1:8000/test-device/FakeSpecificComponent/fake_receive_data",
        timeout=5,
    )
    assert response.status_code == OK
    assert response.json() == 0.5

    response = requests.get(r"http://127.0.0.1:8000/test-device2", timeout=5)
    assert response.status_code == NOT_FOUND
