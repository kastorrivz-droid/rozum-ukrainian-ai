# Conformance Verification Test CVT-001
This test suite verifies the cryptographic interoperability and replay protection features of the Rosum Os Protocol v2.1.

## Mathematical Invariants Verified
- **Private Key Seed (hex)**: `9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60` (TEST-ONLY / NON-PRODUCTION KEY MATERIAL!)
- **Public Key (hex)**: `d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a`
- **JCS(context)**: `{"session_id":"sess_2026_08","state":{"step":1}}`
- **JCS(data)**: `{"stage":4,"task":"crypto_verification"}`
- **question**: `Выполнить верификацию RFC 8785 JCS, digests и signature`
- **Canonical String SHA-256**: `cc10de758f26c00f2a693a3e1dfefed43cb8ba44f2ee2a7e29930127b1a90db5`
- **Ed25519 Signature (Base64)**: `N8SXVRHHrj3RndcFkAx8WsqTH39DqdPCJVLqSvy9raB3zOszADIN+jqubVNZE5P5FomhdzW9/OCoFv62NzcICg==`
