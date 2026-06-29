import json
import urllib.request
from django.conf import settings


def get_clerk_public_keys():
    try:
        url = settings.CLERK_JWKS_URL
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"[Clerk] JWKS fetch failed: {e}")
        return None


def clerk_auth_middleware(get_response):
    def middleware(request):
        request.clerk_user_id = None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"[Clerk] Auth header present: {bool(auth_header)}")

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            print(f"[Clerk] Token first 30 chars: {token[:30]}")

            try:
                import jwt

                jwks = get_clerk_public_keys()
                print(f"[Clerk] JWKS URL used: {settings.CLERK_JWKS_URL}")
                print(f"[Clerk] JWKS keys found: {len(jwks.get('keys', [])) if jwks else 0}")

                if jwks and 'keys' in jwks:
                    for i, key_data in enumerate(jwks['keys']):
                        try:
                            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
                                json.dumps(key_data)
                            )
                            decoded = jwt.decode(
                                token,
                                public_key,
                                algorithms=['RS256'],
                                options={
                                    'verify_aud': False,
                                    'verify_exp': True,
                                }
                            )
                            request.clerk_user_id = decoded.get('sub')
                            print(f"[Clerk] Success. User ID: {request.clerk_user_id}")
                            break
                        except Exception as e:
                            print(f"[Clerk] Key {i} failed: {e}")
                            continue

            except Exception as e:
                print(f"[Clerk] Middleware error: {e}")

        return get_response(request)

    return middleware