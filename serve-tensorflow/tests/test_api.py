"""Tests of the tensorflow image."""

import os
import time
import random as rnd
import requests
from requests.exceptions import ConnectionError
import pytest
import docker


# Settings
PORTS = [8500, 8501]  # the torchserve ports
CONTAINER_PORTS = {f"{port}/tcp": port for port in PORTS}
TIMEOUT_CALL = 5  # the timeout in seconds of the client request call

client = docker.from_env()
container = client.containers.run(
    os.environ["IMAGE_NAME"],
    ports=CONTAINER_PORTS,
    detach=True,
)
time.sleep(20)
container.reload()


def test_container_status():
    """Test that the tensorflow container is running."""
    assert container.status == "running"


def test_container_ports():
    """Test of the expected container ports."""
    assert all(
        PORTS[i] == int(key.split("/")[0])
        for i, (key, _) in enumerate(container.ports.items())
    )


def test_container_access():
    """Test of basic communication with the container returns status 200 (OK)."""
    try:
        url = _get_api_url(container) + "/v1/models/model"
        response = requests.get(url, timeout=TIMEOUT_CALL)
        if response.status_code == 200:
            assert True
    except ConnectionError:
        assert False


def test_health():
    try:
        url = _get_api_url(container) + "/v1/models/model"
        response = requests.get(url, timeout=TIMEOUT_CALL)
        assert response.json()["model_version_status"][0]["state"] == "AVAILABLE"
        assert (
            response.json()["model_version_status"][0]["status"]["error_code"] == "OK"
        )
    except ConnectionError:
        assert False


def test_prediction():
    """Verify that the CNN model can be accessed."""
    data = '{"instances": [1.0, 2.0, 5.0]}'
    answer = [2.5, 3.0, 4.5]
    url = _get_api_url(container) + "/v1/models/model:predict"
    response = requests.post(url, data=data, timeout=TIMEOUT_CALL)
    assert all(x == y for x, y in zip(response.json()["predictions"], answer))


def test_shutdown():
    container.stop()
    container.reload()
    assert container.status == "removing" or container.status == "exited"
    container.remove()
    client.close()

# Private methods


def _get_ip(container):
    """Gets the IP of the container."""
    return container.attrs["NetworkSettings"]["Networks"]["bridge"]["IPAddress"]


def _get_api_url(container):
    """Gets the correct adress for inference."""
    url = "http://{}:{}".format(_get_ip(container), PORTS[1])
    return url


def _get_gRPC_url(container):
    """Gets the correct adress for torchserve management."""
    url = "http://{}:{}}".format(_get_ip(container), PORTS[0])
    return url
