from Crypto.PublicKey import RSA
import base64
import argparse


parser = argparse.ArgumentParser(description='Decode certificate')
parser.add_argument('--file',
                    help='certificate file name', required=True)

args = parser.parse_args()

try:
    with open(args.file, "r") as f:
        key = f.read()
except EnvironmentError: # parent of IOError, OSError *and* WindowsError where available
    print('can not open file: {0}'.format(args.file))
    exit(0)

key_b64 = base64.standard_b64decode(key.encode())
key_priv = RSA.importKey(key_b64)
public_key = key_priv.publickey().exportKey('PEM')
print(key_b64)
print(public_key)




