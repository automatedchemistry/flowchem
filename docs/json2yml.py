#!/usr/bin/env python
import json
import os
import yaml

def json2yml(root, file):
    dir = root + '/' + file
    print(dir)
    yml = yaml.dump(json.load(open(dir)), default_flow_style=False, sort_keys=False)
    yml_dir = dir.split('.')[0] + '_yml.yml'
    with open(yml_dir, 'w') as yaml_file:
        yaml_file.write(yml)

def find_json_files(directory):
    json_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                json2yml(root, file)
    return json_files


if __name__ == '__main__':
    directory = "user-guides/reference/api"  # Update this with your actual directory
    json_files = find_json_files(directory)
