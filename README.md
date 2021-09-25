# anyfs Docker Volume Plugin

## Install

```
# docker plugin install ghcr.io/wtnb75/anyfs
Plugin "ghcr.io/wtnb75/anyfs" is requesting the following privileges:
 - network: [host]
 - mount: [/var/lib/docker/plugins/]
 - device: [/dev/fuse]
 - capabilities: [CAP_SYS_ADMIN]
Do you grant the above permissions? [y/N] y
```

### Uninstall

```
# docker plugin disable ghcr.io/wtnb75/anyfs
# docker plugin uninstall ghcr.io/wtnb75/anyfs
```

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
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: s3fs
      access_key: minio
      secret_key: miniominio
      src: bucket1
      url: http://localhost:9000
      o: use_path_request_style
```

## ftpfs

docker CLI

```
# docker volume create -d ghcr.io/wtnb75/anyfs -o type=curlftpfs -o user=${FTP_USER}:${FTP_PASS} -o src=${FTP_HOST} ftpvol
```

docker compose

```yaml
version: '3'

volumes:
  ftpvol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: curlftpfs
      user: "${FTPUSER}:${FTPPASS}"
      src: ftp-server-hostname
```

## davfs2

(TBD)

## cifs

docker CLI

```
# docker volume create -d ghcr.io/wtnb75/anyfs -o type=cifs -o user=${CIFS_USER} -o pass=${CIFS_PASS} -o src=${CIFS_SHARE} cifsvol
```

docker compose

```yaml
version: '3'

volumes:
  cifsvol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: cifs
      user: ${CIFS_USER}
      pass: ${CIFS_PASS}
      src: //server/share
```

or...

```yaml
version: '3'

volumes:
  cifsvol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: any
      fs_type: cifs
      user: ${USERNAME}
      pass: ${PASSWORD}
      dom: ${DOMAIN}
      src: //server/share
```

## nfs

(TBD)

docker compose

```yaml
version: '3'

volumes:
  nfsvol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: any
      fs_type: nfs
      src: server:/share
```

## sshfs

(TBD)

## download and fuse

(TBD)

fuseiso

```yaml
version: '3'

volumes:
  fuseiso:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: isourl
      src: http://host/path.iso
```

(TBD)

squashfuse

```yaml
version: '3'

volumes:
  fuseiso:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: squashurl
      src: http://host/path.squashfs
```

### note

you can't use loopback mount because it requires too much privileges.

- in container...
  - docker run --privileged ...
  - docker run --cap-add SYS_ADMIN --cap-add MKNOD -v /dev/loop-control:/dev/loop-control --device-cgroup-rule="b 7:* rmw" ...
- in volume plugin...
  - ???

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
    - s3vol:/var/s3vol
    - ftpvol:/var/ftpvol

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
  ftpvol:
    driver: ghcr.io/wtnb75/anyfs
    driver_opts:
      type: curlftpfs
      user: "${FTPUSER}:${FTPPASS}"
      src: ftp-server-hostname
```

# see also

- [Docker volume plugins](https://docs.docker.com/engine/extend/plugins_volume/)
- [vieux/sshfs](https://github.com/vieux/docker-volume-sshfs)
- [FUSE](https://github.com/libfuse/libfuse)
  - [curlftpfs](http://curlftpfs.sourceforge.net/)
  - [s3fs-fuse](https://github.com/s3fs-fuse/s3fs-fuse)
  - [davfs2](https://savannah.nongnu.org/projects/davfs2)
  - [fuseiso](https://sourceforge.net/projects/fuseiso/)
  - [squashfuse](https://github.com/vasi/squashfuse)
