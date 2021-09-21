PLUGIN_NAME = ghcr.io/wtnb75/anyfs
PLUGIN_TAG ?= next

all: clean rootfs create enable

clean:
	rm -rf ./plugin

rootfs:
	docker build -q -t ${PLUGIN_NAME}:rootfs .
	mkdir -p ./plugin/rootfs
	docker create --name tmp ${PLUGIN_NAME}:rootfs
	docker export tmp | tar -x -C ./plugin/rootfs
	cp config.json ./plugin/
	docker rm -vf tmp

create:
	docker plugin rm -f ${PLUGIN_NAME}:${PLUGIN_TAG} || true
	docker plugin create ${PLUGIN_NAME}:${PLUGIN_TAG} ./plugin

enable:
	docker plugin set ${PLUGIN_NAME}:${PLUGIN_TAG} VERBOSE=1
	docker plugin enable ${PLUGIN_NAME}:${PLUGIN_TAG}

disable:
	docker plugin disable -f ${PLUGIN_NAME}:${PLUGIN_TAG}

rm:
	docker plugin rm -f ${PLUGIN_NAME}:${PLUGIN_TAG}

push: clean rootfs create enable
	docker plugin push ${PLUGIN_NAME}:${PLUGIN_TAG}

#run_debug: rootfs
run_debug:
	#docker run -v /dev/fuse:/dev/fuse --cap-add CAP_SYS_ADMIN --network host -ti ${PLUGIN_NAME}:rootfs sh
	docker run --privileged --network host -ti ${PLUGIN_NAME}:rootfs sh
