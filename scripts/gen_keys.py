import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def generate_paseto_keys(target_dir):
    os.makedirs(target_dir, exist_ok=True)
    
    # Generate Ed25519 private key
    private_key = ed25519.Ed25519PrivateKey.generate()
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    with open(os.path.join(target_dir, "paseto_private.pem"), "wb") as f:
        f.write(private_pem)
        
    with open(os.path.join(target_dir, "paseto_public.pem"), "wb") as f:
        f.write(public_pem)
    
    print(f"PASETO Ed25519 keys generated in {target_dir}")

if __name__ == "__main__":
    generate_paseto_keys("keys/paseto")
