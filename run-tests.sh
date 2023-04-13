#!/usr/bin/env bash

# list of QGIS versions to test
QGIS_VERSION_TAGS=( \
  release-3_16 \
  release-3_20 \
  release-3_22 \
  release-3_24 \
  final-3_26_0 \
  final-3_28_0 \
)

# base QGIS docker image
export IMAGE=qgis/qgis

# docker-compose environment variables
export WITH_PYTHON_PEP=false
export ON_TRAVIS=false
export MUTE_LOGS=true

for QGIS_VERSION_TAG in "${QGIS_VERSION_TAGS[@]}"; do
    echo "Running tests for QGIS ${QGIS_VERSION_TAG}"
    docker pull ${IMAGE}:${QGIS_VERSION_TAG}
    docker-compose up -d
    sleep 10
    docker-compose exec -T qgis-testing-environment sh -c "pip3 install flask"
    docker-compose exec -T qgis-testing-environment qgis_testrunner.sh test_suite.test_package
    docker-compose down
done
