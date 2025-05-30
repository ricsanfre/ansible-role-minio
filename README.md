Ansible Role: Minio Server Installation and Configuration
=========

This role install and configure [Minio](http://min.io) in a linux server.


Requirements
------------

None

Role Variables
--------------

Available variables are listed below along with default values (see `defaults\main.yaml`)

- Wheter to install or not minio server and minio client

  ```yml
  minio_install_server: true
  minio_install_client: true
  ```
- Minio server installation details

  Minio UNIX user/group
  ```yml
  minio_group: minio
  minio_user: minio
  ```
  Minio installation directories to place server configuration (`minio_etc_dir`), TLS certificates (`minio_cert_dir`) and user access policies (`minio_policy_dir`)
  ```yml
  minio_etc_dir: /etc/minio
  minio_cert_dir: "{{ minio_etc_dir }}/ssl"
  minio_policy_dir: "{{ minio_etc_dir }}/policy"
  ```
  Minio server IP address (`minio_server_address`), if empty server listen in all available IP addresses, and server/console listening ports (`minio_server_port` and `minio_console_port`)
  ```yml
  minio_server_port: "9091"
  minio_server_addr: ""
  minio_console_port: "9092"
  ```

  Minio admin user and password
  ```yml
  minio_root_user: ""
  minio_root_password: ""
  ```

  Minio site region
  ```yml
  minio_site_region: "eu-west-1"
  ```

  Minio data directories (`minio_server_datadirs`) and whether force the creation in case they do not exist (`minio_server_make_datadirs`)

  ```yml
  minio_server_make_datadirs: true
  minio_server_datadirs:
    - /var/lib/minio
  ```

  ```yaml
  minio_server_cluster_nodes: []
  ```

  Set a list of nodes to create a [distributed cluster (Multi-Node Multi-Drive deployment)](https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-multi-node-multi-drive.html).

  In this mode, ansible will create your server datadirs (`minio_serverdata_dirs`), but use this list (`minio_server_cluster_nodes`) for the server startup.

  > Multi-drive configuration requires datadirs on separate disks to satisfy Minio's distributed storage requirements.

  See recommendations for using, same configuration in all nodes, sequential hostnames and local-atached storage with sequential mounts in the documentation (https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-multi-node-multi-drive.html)

  Example:

  ```yaml
  minio_server_datadirs:
    - '/mnt/disk1/minio'
    - '/mnt/disk2/minio'
    - '/mnt/disk3/minio'
    - '/mnt/disk4/minio'
  minio_server_cluster_nodes:
    - 'https://minio{1...4}.example.net:9091/mnt/disk{1...4}/minio'
  ```

- Minio client configuration

  Connection alias name `minio_alias` and whether validate or not SSL certificates (`minio_validate_certificates`)

  ```yml
  minio_validate_certificate: true
  minio_alias: "myminio"
  ```

- Configuration of TLS

  To enable configuration of TLS set `minio_enable_tls` to true and provide the private key and public certificate as content loaded into `minio_key` and `minio_cert` variables.

  They can be loaded from files using an ansible task like:

  ```yml
  - name: Load tls key and cert from files
  set_fact:
    minio_key: "{{ lookup('file','certificates/{{ inventory_hostname }}_private.key') }}"
    minio_cert: "{{ lookup('file','certificates/{{ inventory_hostname }}_public.crt') }}"

  ```

- Buckets to be created

  Variable `minio_buckets` create the list of provided buckets, and applying a specifc policy. For creating the buckets, a modified version of Ansible Module from Alexis Facques is used (https://github.com/alexisfacques/ansible-module-s3-minio-bucket)

  ```yml
  minio_buckets:
    - name: bucket1
      policy: read-only
    - name: bucket2
      policy: read-write
      object_lock: false
    - name: bucket3
      policy: private
      object_lock: true
  ```
  > NOTE The module use remote connection to Minio Server using Python API (`minio` python package). Role ensure that PIP is installed and install `minio` package.

  During bucket creation three types of policy can be specified: `private`, `read-only` or `read-write` buckets.
  >Reminder: The described configuration enables anonymous access by default.
  >To restrict access by users, you need to specify a  `policy: private`


  Minio object locking can also be enabled or disabled: `true` or `false`.

- Users to be created and buckets ACLs

  Users can be automatically created using  `minio_users` variable: a list of users can be provided, each user with three variables `name` (user name), `password` (user password) and `buckets_acl` list of buckets and type of access granted to each bucket (read-only or read-write).
  The role automatically create policy json files containing the user policy statements and load them into the server.

  Predefined `read-only`,`write-only` and `read-write` policies, containing pre-defined access statements, can be used. Custom policies can be also defined using  `custom` policy. In this case list of access statements need to be provided.


  ```yml
  minio_users:
  - name: user1
    password: supers1cret0
    buckets_acl:
      - name: bucket1
        policy: read-write
      - name: bucket2
        policy: read-only
      - name: bucket3
        policy: custom
        custom:
          - rule: |
              "Effect": "Allow",
              "Action": [
                  "s3:GetObject",
                  "s3:DeleteObject",
                  "s3:PutObject",
                  "s3:AbortMultipartUpload",
                  "s3:ListMultipartUploadParts"
              ],
              "Resource": [
                  "arn:aws:s3:::bucket3/*"
              ]
          - rule: |
              "Effect": "Allow",
              "Action": [
                  "s3:ListBucket"
              ],
              "Resource": [
                  "arn:aws:s3:::bucket3"
              ]
  ```
 The previous configuration will create the following policy.json file for the user

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::bucket1",
                "arn:aws:s3:::bucket1/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::bucket2",
                "arn:aws:s3:::bucket2/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:ListMultipartUploadParts",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::bucket3/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::bucket3"
            ]
        }
    ]
}
```

- Generate Prometheus bearer token

  ```yml
  minio_prometheus_bearer_token: false
  prometheus_bearer_token_output: "{{ minio_etc_dir }}/prometheus_bearer.json"
  ```

  Setting `minio_prometheus_bearer_token` to true, generates a file `/etc/minio/prometheus_bearer.json` which contains the result of executing the command:

  `mc admin prometheus generate myminio -json`


- Install Minio pip library to python virtualenv

  Python virtual env is created to encapsulated installation of required python packages (minio).

  This is to avoid errors pip installation errors in newer python releases, included in Ubuntu 24.04, having a protection on python system packages.

  ```shell
  # pip3 install --upgrade minio
  error: externally-managed-environment

  × This environment is externally managed
  ╰─> To install Python packages system-wide, try apt install
      python3-xyz, where xyz is the package you are trying to
      install.

      If you wish to install a non-Debian-packaged Python package,
      create a virtual environment using python3 -m venv path/to/venv.
      Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
      sure you have python3-full installed.

      If you wish to install a non-Debian packaged Python application,
      it may be easiest to use pipx install xyz, which will manage a
      virtual environment for you. Make sure you have pipx installed.

      See /usr/share/doc/python3.12/README.venv for more information.

  note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
  hint: See PEP 668 for the detailed specification.
  ```

  Location of the virtual environemnt can be configured using following ansible variable:
  ```yaml
  # Path to minio virtual environment, created to avoid breakage with system managed python libraries
  minio_venv_path: "/opt/minio-venv"
  ```

- Site Replication

   Variable `replication_sites` creates the list of multiple independent MinIO deployments to configure as a cluster of replicas called peer sites. For further information on what is replicated across sites refer to the minio documentation (https://min.io/docs/minio/linux/operations/install-deploy-manage/multi-site-replication.html)

  ```yml
  replication_sites:
     - name: myminio2
       url: "http://replication.minio.com:9091"
       admin_user: "myminio2"
       admin_password: "supers1cret02"
   ```
   The `url` is the url of the site that will be replicated to from the currently configured site in the playbook. The `admin_user` and `admin_password` variables are authentication credentials for the site to be replicated to with admin privileges.

   As noted in the `site-replication` documentation
   > - Initially, only **one** of the sites added for replication may have data. After site-replication is successfully configured, this data is replicated to the other (initially empty) sites. Subsequently, objects may be written to any of the sites, and they will be replicated to all other sites.
   > - **Removing a site** is not allowed from a set of replicated sites once configured.
   > - All sites must be using the **same** external IDP(s) if any.
   > - For [SSE-S3 or SSE-KMS encryption via KMS](https://min.io/docs/minio/linux/operations/server-side-encryption.html "MinIO KMS Guide"), all sites **must**  have access to a central KMS deployment. This can be achieved via a central KES server or multiple KES servers (say one per site) connected via a central KMS (Vault) server.


Dependencies
------------

None

Example Playbook
----------------

The following playbook install and configure minio server and client, enabling TLS and generating self-signed SSL certificates.
It also create some buckets and users with proper ACLs

```yml
---
- name: Install and configure Minio Server
  hosts: minio
  become: true
  gather_facts: true
  vars:
    server_hostname: minio.example.com
    ssl_key_size: 4096
    ssl_certificate_provider: selfsigned

  pre_tasks:
    - name: Generate self-signed SSL certificates for minio
      include_tasks: generate_selfsigned_cert.yml
      args:
        apply:
          delegate_to: localhost
          become: false
    - name: Load tls key and cert
      set_fact:
        minio_key: "{{ lookup('file','certificates/' + inventory_hostname + '_private.key') }}"
        minio_cert: "{{ lookup('file','certificates/' + inventory_hostname + '_public.crt') }}"

  roles:
    - role: ricsanfre.minio
      minio_root_user: "miniadmin"
      minio_root_password: "supers1cret0"
      minio_enable_tls: true
      minio_buckets:
        - name: bucket1
          policy: read-write
        - name: bucket2
          policy: read-write
      minio_users:
        - name: user1
          password: supers1cret0
          buckets_acl:
            - name: bucket1
              policy: read-write
            - name: bucket2
              policy: read-only

```

`pre-tasks` section include tasks to generate a private key and a self-signed certificate and load them into `minio_key` and `minio_cert` variables.

Where `generate_selfsigned_cert.yml` contain the tasks for generating a Private Key and SSL self-signed certificate:

```yml
---
- name: Create private certificate
  openssl_privatekey:
    path: "certificates/{{ inventory_hostname }}_private.key"
    size: "{{ ssl_key_size | int }}"
    mode: 0644

- name: Create CSR
  openssl_csr:
    path: "certificates/{{ inventory_hostname }}_cert.csr"
    privatekey_path: "certificates/{{ inventory_hostname }}_private.key"
    common_name: "{{ server_hostname }}"

- name: Create certificates for keystore
  openssl_certificate:
    csr_path: "certificates/{{ inventory_hostname }}_cert.csr"
    path: "certificates/{{ inventory_hostname }}_public.crt"
    privatekey_path: "certificates/{{ inventory_hostname }}_private.key"
    provider: "{{ ssl_certificate_provider }}"

```


License
-------

MIT

Author Information
------------------

Created by Ricardo Sanchez (ricsanfre)
Bucket creation ansible module based on module from Alexix Facques (https://github.com/alexisfacques/ansible-module-s3-minio-bucket)
