Place the server certificate chain here if needed by the application.

Usage:

- Obtain the PEM chain (example):

  openssl s_client -showcerts -servername ivscc.oan.es -connect ivscc.oan.es:443 </dev/null \
    | sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' > ivscc_chain.pem

- Copy the resulting `ivscc_chain.pem` to this folder and commit if you want the
  application to trust the chain when `IVS_CA_BUNDLE` is not set.

Notes:
- Shipping third-party CA material may have policy/security implications.
- Prefer setting `IVS_CA_BUNDLE` in deployment to point to a maintained CA bundle.
