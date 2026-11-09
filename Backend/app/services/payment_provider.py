"""Sandbox-only payment adapter. It never sends credentials, collects funds, or initiates payouts."""
import hashlib,secrets
from dataclasses import dataclass

@dataclass(frozen=True)
class SandboxIntent:
    provider_reference:str
    callback_token:str

class SandboxPaymentProvider:
    code='TRAVELLY_SANDBOX'
    def create_intent(self):
        return SandboxIntent('SBX-'+secrets.token_hex(12).upper(),secrets.token_urlsafe(48))
    def callback_hash(self,token):return hashlib.sha256(token.encode()).hexdigest()
    def verify_callback(self,payment,reference,token):
        return payment.provider_reference==reference and secrets.compare_digest(payment.provider_callback_hash or '',self.callback_hash(token))

provider=SandboxPaymentProvider()
