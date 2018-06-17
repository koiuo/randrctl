BUILD_DIR=build
ZIPAPP=${BUILD_DIR}/zipapp
RANDRCTL=randrctl
BINARY=${BUILD_DIR}/${RANDRCTL}

default: bin
.PHONY: bin
bin: ${BINARY}

${BUILD_DIR}:
	mkdir -p ${BUILD_DIR}

${ZIPAPP}: ${BUILD_DIR}
	mkdir -p ${ZIPAPP}
	pip install -t ${ZIPAPP} .

${BINARY}: ${ZIPAPP}
	python3 -m zipapp ${ZIPAPP} --main 'randrctl.cli:main' --python '/usr/bin/env python3' --output ${BINARY}

.PHONY: test
test:
	python setup.py test

.PHONY: clean
clean:
	rm -rf ${BUILD_DIR}
