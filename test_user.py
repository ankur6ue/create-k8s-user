import configparser
import os
from requests import ConnectionError, HTTPError
import urllib3
import ssl
import yaml
import tempfile
import base64
from kubernetes import client, config

## This code demonstrates accessing the kubernetes API server directly using urllib and passing in the user
## ssl certificate required for authentication

def _create_temp_file_with_content(content, temp_file_path=None):
    fd, name = tempfile.mkstemp(dir=temp_file_path)
    os.close(fd)
    with open(name, 'wb') as fd:
        fd.write(content.encode() if isinstance(content, str) else content)
    return name


def run():
    cfgp = configparser.ConfigParser()
    cfgp.read('user_settings.cfg')
    # Cluster name
    cluster_name = cfgp['DEFAULT']['CLUSTER_NAME']
    # user name
    user_name = cfgp['DEFAULT']['USER_NAME']
    # path to your kubernetes cluster config
    kube_cfg_path = cfgp['DEFAULT']['KUBE_CONFIG_PATH']

    # Read kubeconfig. The kubeconfig file stores the following pieces of information:
    #
    # 1. Info about your kubernetes clusters such as the certificate
    # authority data, server address and name for each cluster. For example, you may have a local kubernetes cluster
    # set up on your development computer and another one on AWS. The same config file will have info about each
    # cluster. For more information about certificate authority data, see this:
    # https://medium.com/talpor/ssl-tls-authentication-explained-86f00064280

    # 2. List of contexts. A context is a set of cluster names, users, namespaces and other info. You can set a context
    # by using kubectl config set-context command. Upon doing so, calls to the kubernetes API server will use the server
    # name, user and namespace specific to that context

    # 3. A list of users: This section contains the client-certificate-data and key-data for each user.

    with open(os.path.join(kube_cfg_path, 'config'), "r") as stream:
        try:
            conf = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Go through all clusters and get info about the one we are interested in
    cluster_idx = None
    clusters = conf['clusters']
    for idx, cluster in enumerate(clusters):
        if cluster["name"] == cluster_name:
            cluster_idx = idx

    # Go through all users and get ssl info for the one we are interested
    user_idx = None
    users = conf['users']
    for idx, user in enumerate(users):
        if user["name"] == user_name:
            user_idx = idx

    # To make API calls to the kubernetes API server we need:
    # 1.Server specific info:
    #   1a: certificate authority data for the server
    #   1b: server address
    # 2. user specific info:
    #   2a: certificate issued by kubernetes certificate issuer
    #   2b: private key for the user. This key isn't actually passed to the API server, it is used during SSL handshake
    #       by urllib

    # server specific info
    ca_cert_data = conf['clusters'][cluster_idx]['cluster']['certificate-authority-data']
    ca_cert = _create_temp_file_with_content(base64.standard_b64decode(ca_cert_data.encode()))
    server_name = conf['clusters'][cluster_idx]['cluster']['server']

    # user specific info
    # read certificate info issued by the certificate issuer
    client_cert_data = conf['users'][user_idx]['user']['client-certificate-data']
    cert_file = _create_temp_file_with_content(base64.standard_b64decode(client_cert_data.encode()))

    # read private key (this is only required for ssl handshake and is not sent to the API server)
    client_key_data = conf['users'][user_idx]['user']['client-key-data']
    key_file = _create_temp_file_with_content(base64.standard_b64decode(client_key_data.encode()))

    # Can also read this info from the files stored in the certs directory
    read_from_certs = False
    if read_from_certs:
        cert_file_b64 = 'certs/dev1.crt'
        # Read user ssl info
        with open(cert_file_b64, "r") as f:
            client_cert_data = f.read()
            cert_file = _create_temp_file_with_content(base64.standard_b64decode(client_cert_data.encode()))

        key_file = 'certs/dev1.key'
        with open(key_file, "r") as f:
            client_key_data = f.read()
            key_file = _create_temp_file_with_content(base64.standard_b64decode(client_key_data.encode()))


    # Creating a PoolManager instance for sending requests.
    pool_manager = urllib3.PoolManager(
        num_pools=4,
        maxsize=100,
        cert_reqs=ssl.CERT_REQUIRED,
        ca_certs=ca_cert,
        cert_file=cert_file,
        key_file=key_file
    )
    http = urllib3.PoolManager()

    # Get all pods in the development namespace by making a REST API call to Kubernetes API server
    url = server_name + "/api/v1/namespaces/development/pods"
    headers = {'Accept': 'application/json', 'User-Agent': 'OpenAPI-Generator/20.13.0/python',
               'Content-Type': 'application/json'}

    # Sending a GET request and getting back response as HTTPResponse object.
    try:
        resp = pool_manager.request("GET", url, headers)
    except HTTPError as e:
        print('The server couldn\'t fulfill the request, error code: {0}'.format(e.code))
    except ConnectionError:
        print('We failed to reach a server.')

    print(resp.data)

    # Get all pods in the kube-system namespace by making a REST API call to Kubernetes API server
    url = server_name + "/api/v1/namespaces/default/pods"
    headers = {'Accept': 'application/json', 'User-Agent': 'OpenAPI-Generator/20.13.0/python',
               'Content-Type': 'application/json'}

    # Sending a GET request and getting back response as HTTPResponse object.
    try:
        resp = pool_manager.request("GET", url, headers)
    except HTTPError as e:
        print('The server couldn\'t fulfill the request, error code: {0}'.format(e.code))
    except ConnectionError:
        print('We failed to reach a server.')

    print(resp.data)

    # Let's now use the kubernetes python ASK to access all pods in the default namespace
    # This is how you'd access the kubernetes API server using Kubernetes Python SDK
    config.load_kube_config()  # this loads the default config which has full priveleges and can print the podnames
    # in the default namespace
    v1 = client.CoreV1Api()
    # print("Listing pods with their IPs:")
    ret = v1.list_namespaced_pod(namespace='kube-system', watch=False)
    for i in ret.items:
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

    # Now load the dev1 config
    config.load_kube_config(context='dev1.k8s.local')
    v1 = client.CoreV1Api()
    # dev1 context lacks the required priveleges and will throw exception
    print("using dev1 profile")
    try:
        ret = v1.list_namespaced_pod(namespace='kube-system', watch=False)
        for i in ret.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
    except:
        print("Access Denied")


if __name__ == '__main__':
    run()
