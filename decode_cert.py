
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64
import argparse

parser = argparse.ArgumentParser(description='Decode certificate')
parser.add_argument('--file',
                    help='certificate file name', required=True)

args = parser.parse_args()

try:
    with open(args.file, "r") as f:
        cert = f.read()
except EnvironmentError: # parent of IOError, OSError *and* WindowsError where available
    print('can not open file: {0}'.format(args.file))
    exit(0)

cert_b64 = base64.standard_b64decode(cert.encode())
cert = x509.load_pem_x509_certificate(cert_b64, default_backend())
print(cert.subject)




