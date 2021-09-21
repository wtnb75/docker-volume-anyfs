# test

## minio

### boot minio and create bucket

- cd ../servers && docker compose up -d s3 && cd -
- vi .s3cfg.minio

```
access_key = minio
secret_key = miniominio
bucket_location = us-east-1
use_https = False
host_base = localhost:9000
host_bucket = localhost:9000
signature_v2 = False
```

- s3cmd -c .s3cfg.minio mb s3://bucket1

### setup s3fs and test

- docker compose -f minio.yml up -d
- docker compose -f minio.yml exec testminio dd if=/dev/zero count=1 of=/xyz/zero1
- docker compose -f minio.yml exec testminio ls /xyz
- s3cmd -c .s3cfg.minio ls s3://bucket1

### cleanup

- docker compose -f minio.yml down -v
- cd ../servers && docker compose down -v && cd -

## webdav

- cd ../servers && docker compose up -d webdav && cd -


## ftp

## sftp

## cifs

## nfs
