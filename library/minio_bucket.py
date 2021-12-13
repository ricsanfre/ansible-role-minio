#!/usr/bin/env python
# coding: utf-8

DOCUMENTATION = """
---
module: minio_bucket
author:
    - "Alexis Facques" (@alexisfacques)
short_description: Creates minio s3 buckets
description:
    - "Minio S3 buckets use policies and not ACLs, making modules 'aws_s3' and
      's3 bucket' incompatible"
options:
    s3_url:
        description:
            - The name or IP address of the name server to query.
        required: true
    region:
        description:
            - Region name of buckets in S3 service
        required: false
    name:
        description:
            - The name of the S3 bucket.
        required: true
    access_key:
        description:
            - S3 access key.
        required: true
    secret_key:
        description:
            - S3 secret_key.
        required: true
    state:
        description:
            - Create or remove the s3 bucket.
        required: false
    policy:
        description:
            - Policies to bind to the s3 bucket.
        required: false
    validate_certs:
        description:
            - When set to "no", SSL certificates will not be validated for
              boto versions >= 2.6.0.
        required: false
"""

EXAMPLES = """
- minio_bucket:
    s3_url: s3.min.io
    name: my_bucket
    access_key: my_access_key
    secret_key: my_secret_key
    policy:
      - *:read-only
    state: present
"""

from ansible.module_utils.basic import AnsibleModule

import re
import urllib3
import json

from minio import Minio
from minio.error import S3Error

class UncheckedException(Exception):
   pass

class REMatcher:
    def __init__(self, string):
        """
        Adapted from: https://stackoverflow.com/a/2555047/7152435
        A handy little class that retains the matched groups of a re.match
        result.
        """
        self.__string = string

    def match(self, regexp):
        """
        Returns whether or not the tested "self.__string" matches "regexp".
        """
        self.rematch = re.match(regexp, self.__string)
        return bool(self.rematch)

    def group(self, i):
        """
        Returns the capture group "i" of the prior match, if any.
        """
        return self.rematch.group(i)

def get_ro_statements(bucket_name):
    return [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": ["*"]
            },
            "Action": ["s3:GetBucketLocation"],
            "Resource": ["arn:aws:s3:::%s" % bucket_name]
        }, {
            "Effect": "Allow",
            "Principal": {
                "AWS":["*"]
            },
            "Action": ["s3:ListBucket"],
            "Resource": ["arn:aws:s3:::%s" % bucket_name]
        }, {
            "Effect": "Allow",
            "Principal": {
                "AWS":["*"]
            },
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::%s/*" % bucket_name]
        }
    ]

def get_wo_statements(bucket_name):
    return [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": ["*"]
            },
            "Action": ["s3:ListBucketMultipartUploads","s3:GetBucketLocation"],
            "Resource": ["arn:aws:s3:::%s" % bucket_name]
        }, {
            "Effect": "Allow",
            "Principal": {
                "AWS": ["*"]
            },
            "Action": [
                "s3:PutObject",
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:ListMultipartUploadParts"
            ],
            "Resource": ["arn:aws:s3:::%s/*" % bucket_name]
        }
    ]

def get_rw_statements(bucket_name):
    return [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": ["*"]
            },
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads"
            ],
            "Resource": ["arn:aws:s3:::%s" % bucket_name]
        }, {
            "Effect":"Allow",
            "Principal":{
                "AWS":["*"]
            },
            "Action":[
                "s3:GetObject",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:AbortMultipartUpload",
                "s3:DeleteObject"
            ],
            "Resource":["arn:aws:s3:::%s/*" % bucket_name]
        }
    ]

def main():
    exit_message = dict(failed=False)

    module = AnsibleModule(
        argument_spec=dict(
            s3_url=dict(required=True, type="str"),
            region=dict(required=False, type="str", default="us-west-1"),
            name=dict(required=True, type="str"),
            access_key=dict(required=True, type="str"),
            secret_key=dict(required=True, type="str"),
            state=dict(required=False, type="str", default="present", choices=["absent","present"]),
            policy=dict(required=False, type="str", choices=["read-only","write-only","read-write"]),
            validate_certs=dict(required=False, type="bool", default=True)
        ),
        # No changes will be made to this environment with this module
        supports_check_mode=True
    )

    bucket_name = module.params["name"]
    policy = module.params["policy"]
    m = REMatcher(module.params["s3_url"])

    if m.match(r"^http://([\w./:]+)"):
        is_https = False
        unschemed_s3_url = m.group(1)

    elif m.match(r"^https://([\w./:]+)"):
        is_https = True
        unschemed_s3_url = m.group(1)

    elif m.match(r"^(?:[a-zA-Z0-9]+:\/\/)*([\w./:]+)"):
        is_https = True
        unschemed_s3_url = m.group(1)
        
    else:
        raise UncheckedException("Unhandled structure for 's3_url'.")

    http_client = None if module.params["validate_certs"] \
        else urllib3.PoolManager(
            timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
            cert_reqs='CERT_NONE'
        )

    try:
        client = Minio(
            unschemed_s3_url,
            access_key=module.params["access_key"],
            secret_key=module.params["secret_key"],
            secure=is_https,
            region=module.params["region"],
            http_client=http_client
        )

        if module.params["state"] == "absent":
            if module.check_mode:
                module.exit_json(
                    faised=False,
                    changed=client.bucket_exists(bucket_name)
                )

            elif client.bucket_exists(bucket_name):
                client.remove_bucket(bucket_name)
                exit_message = dict(failed=False, changed=True)

            else:
                exit_message = dict(failed=False, changed=False)

        else:
            if module.check_mode:
                module.exit_json(faised=False, changed=True)

            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                if policy:
                    client.set_bucket_policy(bucket_name, json.dumps({
                        "Version": "2012-10-17",
                        "Statement": get_ro_statements(bucket_name) \
                            if policy == "read-only" else \
                            get_wo_statements(bucket_name) \
                            if policy == "write-only" else \
                            get_rw_statements(bucket_name)
                    }))
                exit_message = dict(failed=False, changed=True)
            else:
                exit_message = dict(failed=False, changed=False)

    except urllib3.exceptions.MaxRetryError:
        exit_message = dict(
            failed=True,
            msg="Could not connect to '%s'." % unschemed_s3_url
        )

    except Exception as e:
        exit_message = dict(
            failed=True,
            msg="An error has occured with the \"minio_bucket\" module: %s" % e
        )

    if exit_message["failed"]:
        module.fail_json(**exit_message)

    else:
        module.exit_json(**exit_message)

if __name__ == "__main__":
    main()