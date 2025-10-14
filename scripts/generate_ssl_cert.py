#!/usr/bin/env python3
"""
Generate self-signed SSL certificates for development purposes.
For production, use certificates from a trusted CA (e.g., Let's Encrypt).
"""
import os
import sys
from datetime import datetime, timedelta


def generate_ssl_certificates(cert_dir='certs'):
    """
    Generate self-signed SSL certificate and key for HTTPS support.
    
    Args:
        cert_dir: Directory to store certificates (default: 'certs')
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        print("Error: cryptography package is required.")
        print("Install it with: pip install cryptography")
        sys.exit(1)

    # Create certs directory if it doesn't exist
    os.makedirs(cert_dir, exist_ok=True)
    
    cert_path = os.path.join(cert_dir, 'cert.pem')
    key_path = os.path.join(cert_dir, 'key.pem')
    
    # Check if certificates already exist
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"SSL certificates already exist in {cert_dir}/")
        print(f"  - Certificate: {cert_path}")
        print(f"  - Private Key: {key_path}")
        response = input("Do you want to regenerate them? (y/N): ").strip().lower()
        if response != 'y':
            print("Using existing certificates.")
            return cert_path, key_path
    
    print("Generating self-signed SSL certificate...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Development"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"StockSense Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now()
    ).not_valid_after(
        datetime.now() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.DNSName(u"127.0.0.1"),
            x509.DNSName(u"0.0.0.0"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Write private key to file
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate to file
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"✅ SSL certificates generated successfully!")
    print(f"  - Certificate: {cert_path}")
    print(f"  - Private Key: {key_path}")
    print("\n⚠️  These are self-signed certificates for DEVELOPMENT only.")
    print("For PRODUCTION, use certificates from a trusted CA (e.g., Let's Encrypt).")
    print("\nYour browser will show a security warning for self-signed certificates.")
    print("You can safely proceed by accepting the certificate in development.")
    
    return cert_path, key_path


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate self-signed SSL certificates for StockSense'
    )
    parser.add_argument(
        '--cert-dir',
        default='certs',
        help='Directory to store certificates (default: certs)'
    )
    
    args = parser.parse_args()
    generate_ssl_certificates(args.cert_dir)
