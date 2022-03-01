#!/bin/bash

USERNAME=${1}
GRPNAME=${2}
echo + Creating private key: ${USERNAME}.key
openssl genrsa -out ${USERNAME}.key 4096

echo + Creating signing request: ${USERNAME}.csr
openssl req -new -key ${USERNAME}.key -out ${USERNAME}.csr -subj "/CN=${USERNAME}/O=${GRPNAME}"

cp signing-request-template.yaml ${USERNAME}-signing-request.yaml
sed -ri 's/^(\s*)(name\s*:\s*dev\s*$)/\1name: '"${USERNAME}"-csr'/' ${USERNAME}-signing-request.yaml

B64=`cat ${USERNAME}.csr | base64 | tr -d '\n'`
sed -ri 's/^(\s*)(request\s*:\s*BLAH\s*$)/\1request: '"${B64}"'/' ${USERNAME}-signing-request.yaml

echo + Creating signing request in kubernetes
kubectl delete -f ${USERNAME}-signing-request.yaml
kubectl create -f ${USERNAME}-signing-request.yaml

echo + List of signing requests
kubectl get csr

echo + Approving CSR
kubectl certificate approve ${USERNAME}-csr

echo + Writing certificate to ${USERNAME}.crt
CERT=`kubectl get csr ${USERNAME}-csr -o jsonpath='{.status.certificate}'`
echo ${CERT} > certs/${USERNAME}.crt

echo + Writing key to ${USERNAME}.key
KEY=`cat ${USERNAME}.key | base64 | tr -d '\n'`
echo ${KEY} > certs/${USERNAME}.key