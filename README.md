# anyfs Docker Volume Plugin

## Install

```
# docker plugin install ghcr.io/wtnb75/anyfs
# docker plugin enable ghcr.io/wtnb75/anyfs
```

### Uninstall

- docker plugin disable ghcr.io/wtnb75/anyfs
- docker plugin uninstall ghcr.io/wtnb75/anyfs

## s3fs-fuse

docker CLI

```
# docker volume create -d ghcr.io/wtnb75/anyfs -o type=s3fs -o access_key=${AWS_ACCESS_KEY} -o secret_key=${AWS_SECRET_KEY} -o endpoint=${AWS_REGION} -o url=https://s3-${AWS_REGION}.amazonaws.com -o src=${AWS_BUCKET} s3vol
```

docker compose

```yaml
version: '3'

volumes:
  s3vol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: s3fs
      access_key: ${AWS_ACCESS_KEY}
      secret_key: ${AWS_SECRET_KEY}
      src: ${AWS_BUCKET}
      endpoint: ${AWS_REGION}
      url: https://s3-${AWS_REGION}.amazonaws.com
```

minio example

```yaml
version: '3'

volumes:
  miniovol:
    driver: ghcr.io/wtnb75/anyfs:next
    driver_opts:
      type: s3fs
      access_key: minio
      secret_key: miniominio
      src: bucket1
      url: http://localhost:9000
      o: use_path_request_style
```

## davfs2

## cifs

## nfs

## download and fuse

- fuseiso
- squashfuse

### note

you can't use loopback mount because it requires too much privileges.

- in container...
  - docker run --privileged ...
  - docker run --cap-add SYS_ADMIN --cap-add MKNOD -v /dev/loop-control:/dev/loop-control --device-cgroup-rule="b 7:* rmw" ...
- in volume plugin...
  - ?

## Use from docker compose

```yaml
version: '3'

services:
  name:
    image: alpine:3
    command:
    - sleep
    - infinity
    volumes:
    - s3vol1:/var/s3vol
    - davvol1:/var/davvol

volumes:
  s3vol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: s3fs
      access_key: ${AWS_ACCESS_KEY}
      secret_key: ${AWS_SECRET_KEY}
      src: ${AWS_BUCKET}
      endpoint: ${AWS_REGION}
      url: https://s3-${AWS_REGION}.amazonaws.com
  davvol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: davfs2
      url: https://dav-host/path
      username: ${DAV_USERNAME}
      password: ${DAV_PASSWORD}
```
