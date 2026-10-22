# Pool TLS trust policy

Known pools use certificate-specific trust anchors with exact SHA-256 leaf pins,
OpenSSL certificate signature/validity checking and TLS 1.2 or newer. This is not
public-CA validation: historical pool certificates have no DNS subjectAltName.
The exact certificate pin is bound to an exact allowlisted DNS host instead.

No arbitrary certificate is accepted. A new or rotated certificate fails closed.
There is no automatic enrollment, pin refresh, plaintext fallback, Windows trust
store modification, or mining data sent before verification completes.
Unknown hosts use ordinary CA chain and hostname verification.

Initial pin provenance: direct certificate-only inspection of the selected pool,
corroborated against public historical fingerprint records. These pins were not
published as CA certificates by the pool operator. The pinned certificate's
private key remains the basis of server authentication; this is not a guarantee
about the pool operator or a security certification of the application.

HashVault: 420c7850e09b7c0bdcf748a7da9eb3647daf8515718f36d9ccfdd6b9ff834b14
MoneroOcean: 239daadd5c7d0ac097376c7871f787738826eef1c024729eff870e473b970855

Pool endpoint policies were checked against their HTTPS public port APIs.
Historical MoneroOcean fingerprint observation:
https://github.com/xmrig/xmrig/issues/3404
