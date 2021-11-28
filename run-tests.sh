#!/usr/bin/env bash

QGIS_IMAGE=qgis/qgis

QGIS_IMAGE_V_3_16=release-3_16
QGIS_IMAGE_V_3_20=release-3_20

QGIS_VERSION_TAGS=($QGIS_IMAGE_V_3_16 $QGIS_IMAGE_V_3_20)

export IMAGE=$QGIS_IMAGE

for TAG in "${QGIS_VERSION_TAGS[@]}"
do
    echo "Running tests for QGIS $TAG"
    export QGIS_VERSION_TAG=$TAG
    export WITH_PYTHON_PEP=false
    export ON_TRAVIS=false
    export MUTE_LOGS=true

    docker-compose up -d

    sleep 10
    docker-compose exec -T qgis-testing-environment sh -c "pip3 install flask"

    docker-compose exec -T qgis-testing-environment qgis_testrunner.sh test_suite.test_package
    docker-compose down

done
