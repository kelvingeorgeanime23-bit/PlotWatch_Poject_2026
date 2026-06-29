from django.conf import settings


def clerk_settings(request):
	"""
	Makes Clerk's publishable key, accounts URL, and frontend API
	domain available in every template automatically.
	"""
	return {
		'clerk_publishable_key': settings.CLERK_PUBLISHABLE_KEY,
		'clerk_accounts_url': settings.CLERK_ACCOUNTS_URL,
		'clerk_frontend_api_url': settings.CLERK_FRONTEND_API_URL,
	}