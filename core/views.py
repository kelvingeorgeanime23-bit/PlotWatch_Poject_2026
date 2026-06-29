from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.urls import reverse
from datetime import date, timedelta
from .models import Tenant, Landlord, Payment, WaterBill, ElectricityBill, MaintenanceRequest, House, HousePhoto, ContactMessage
import json


def home(request):
	"""
	Public marketing homepage. Shows a small live preview of open
	houses pulled straight from the database, not placeholder
	copy, and a true count of houses on the plot for the hero
	stat pill.
	"""
	preview_houses = House.objects.filter(is_occupied=False).select_related('landlord').order_by('house_id')[:3]
	total_houses = House.objects.count()
	return render(request, 'home.html', {
		'preview_houses': preview_houses,
		'total_houses': total_houses,
	})


def dashboard(request):
	"""
	Role-based redirect hub.
	Clerk sends everyone here after sign in.
	Django checks the Clerk user ID against the database
	and redirects to the correct dashboard.
	"""
	return render(request, 'dashboard.html')


def tenant_dashboard(request):
	return render(request, 'tenant_dashboard.html')


@require_http_methods(["GET"])
def role_check_api(request):
	"""
	Called by dashboard.html JavaScript after Clerk loads.
	Receives the Clerk user ID and returns the user's role.
	Role comes only from the verified Clerk token, never from
	Django's own session, so a stale Django admin session in the
	browser can never leak into this check.

	When the verified Clerk ID matches ADMIN_CLERK_USER_ID, this
	logs Vanessa into Django's own session, but only the first
	time. django_login() rotates the CSRF token every time it
	runs, even for an already-logged-in user, so calling it on
	every single page load was quietly invalidating any admin
	page that was already open. The is_authenticated check below
	makes sure it only fires once per session.
	"""
	clerk_user_id = getattr(request, 'clerk_user_id', None)

	if not clerk_user_id:
		return JsonResponse({'role': 'unknown'}, status=200)

	if settings.ADMIN_CLERK_USER_ID and clerk_user_id == settings.ADMIN_CLERK_USER_ID:
		if not (request.user.is_authenticated and request.user.is_staff):
			try:
				admin_user = User.objects.get(username='vanessa', is_staff=True)
				django_login(request, admin_user)
			except User.DoesNotExist:
				pass
		return JsonResponse({'role': 'admin', 'redirect': '/admin/'})

	if Tenant.objects.filter(clerk_user_id=clerk_user_id, is_active=True).exists():
		return JsonResponse({'role': 'tenant', 'redirect': '/tenant/'})

	if Landlord.objects.filter(clerk_user_id=clerk_user_id).exists():
		return JsonResponse({'role': 'landlord', 'redirect': '/landlord/'})

	return JsonResponse({'role': 'unregistered', 'redirect': '/'})


@require_http_methods(["GET"])
def tenant_dashboard_api(request):
	"""
	Returns everything the tenant dashboard needs in one call:
	this month's bill summary, the tenant's profile, their house
	details, and the full history for rent, water, and
	electricity. Bundled into one response on purpose, so the
	page only makes one network call on load instead of five,
	which matters on a slow phone connection.
	"""
	clerk_user_id = getattr(request, 'clerk_user_id', None)

	if not clerk_user_id:
		return JsonResponse({'error': 'Not authenticated'}, status=401)

	try:
		tenant = Tenant.objects.get(clerk_user_id=clerk_user_id, is_active=True)
	except Tenant.DoesNotExist:
		return JsonResponse({'error': 'Tenant not found'}, status=404)

	today = date.today()
	current_month = today.replace(day=1)

	# Rent, this month only, for the summary card.
	rent_data = None
	rent = Payment.objects.filter(tenant=tenant, month=current_month).first()
	if rent:
		rent_data = {
			'amount': str(rent.amount),
			'status': rent.status,
			'date_paid': str(rent.date_paid) if rent.date_paid else None
		}

	# Water, this month, summed across every entry. Water is
	# collected weekly, so a single month can have several rows.
	water_this_month = WaterBill.objects.filter(
		tenant=tenant,
		date__month=today.month,
		date__year=today.year
	)
	water_data = None
	if water_this_month.exists():
		total_amount = sum(w.amount for w in water_this_month)
		all_paid = all(w.status == 'paid' for w in water_this_month)
		water_data = {
			'amount': str(total_amount),
			'status': 'paid' if all_paid else 'pending'
		}

	# Electricity, this month, only relevant for houses on a
	# monthly bill rather than a token meter.
	elec_data = None
	if tenant.house and tenant.house.electricity_type == 'monthly':
		elec = ElectricityBill.objects.filter(
			tenant=tenant, month=current_month
		).first()
		if elec:
			elec_data = {
				'amount': str(elec.amount),
				'status': elec.status
			}

	household_members = [
		{'full_name': m.full_name, 'relationship': m.get_relationship_display()}
		for m in tenant.household_members.all()
	]

	# Profile details for the profile sheet.
	profile_data = {
		'full_name': tenant.full_name,
		'email': tenant.email,
		'phone_number': tenant.phone_number,
		'id_number': tenant.id_number,
		'emergency_contact_name': tenant.emergency_contact_name,
		'emergency_contact_phone': tenant.emergency_contact_phone,
		'move_in_date': str(tenant.move_in_date),
	}

	# House details for the house sheet.
	house_detail_data = None
	if tenant.house:
		house_detail_data = {
			'house_id': tenant.house.house_id,
			'house_type': tenant.house.get_house_type_display(),
			'monthly_rent': str(tenant.house.monthly_rent),
			'deposit_amount': str(tenant.house.deposit_amount),
			'electricity_type': tenant.house.get_electricity_type_display(),
			'move_in_date': str(tenant.move_in_date),
		}

	# Full history, most recent first, capped at 50 rows so a
	# long-staying tenant doesn't pull down an unbounded list.
	rent_history = [
		{
			'month': str(p.month),
			'amount': str(p.amount),
			'status': p.status,
			'date_paid': str(p.date_paid) if p.date_paid else None,
		}
		for p in Payment.objects.filter(tenant=tenant).order_by('-month')[:50]
	]

	water_history = [
		{
			'date': str(w.date),
			'jerrican_type': w.jerrican_type,
			'quantity': w.quantity,
			'amount': str(w.amount),
			'status': w.status,
			'date_paid': str(w.date_paid) if w.date_paid else None,
		}
		for w in WaterBill.objects.filter(tenant=tenant).order_by('-date')[:50]
	]

	electricity_history = [
		{
			'month': str(e.month),
			'units_used': str(e.units_used) if e.units_used is not None else None,
			'amount': str(e.amount),
			'status': e.status,
			'date_paid': str(e.date_paid) if e.date_paid else None,
		}
		for e in ElectricityBill.objects.filter(tenant=tenant).order_by('-month')[:50]
	]

	return JsonResponse({
		'house_id': tenant.house.house_id if tenant.house else None,
		'electricity_type': tenant.house.electricity_type if tenant.house else None,
		'rent': rent_data,
		'water': water_data,
		'electricity': elec_data,
		'household_members': household_members,
		'profile': profile_data,
		'house_detail': house_detail_data,
		'rent_history': rent_history,
		'water_history': water_history,
		'electricity_history': electricity_history,
	})


@csrf_exempt
@require_http_methods(["POST"])
def tenant_maintenance_api(request):
	clerk_user_id = getattr(request, 'clerk_user_id', None)

	if not clerk_user_id:
		return JsonResponse({'error': 'Not authenticated'}, status=401)

	try:
		tenant = Tenant.objects.get(clerk_user_id=clerk_user_id, is_active=True)
	except Tenant.DoesNotExist:
		return JsonResponse({'error': 'Tenant not found'}, status=404)

	try:
		body = json.loads(request.body)
		category = body.get('category', '')
		description = body.get('description', '')

		valid_categories = ['roof', 'plumbing', 'electrical', 'door', 'window', 'other']
		if category not in valid_categories:
			return JsonResponse({'error': 'Invalid category'}, status=400)

		if len(description) < 10:
			return JsonResponse({'error': 'Description too short'}, status=400)

		MaintenanceRequest.objects.create(
			tenant=tenant,
			category=category,
			description=description,
			status='open'
		)

		return JsonResponse({'success': True})

	except Exception:
		return JsonResponse({'error': 'Server error'}, status=500)


@require_http_methods(["GET"])
def landlord_dashboard_api(request):
	"""
	Returns every house this landlord owns, the current tenant on
	each occupied house with exact bill amounts (not just a
	status word), the full list of open maintenance requests per
	house, one combined list of every open issue across the whole
	portfolio sorted oldest first, and the landlord's own profile
	details for the profile sheet.
	"""
	clerk_user_id = getattr(request, 'clerk_user_id', None)

	if not clerk_user_id:
		return JsonResponse({'error': 'Not authenticated'}, status=401)

	try:
		landlord = Landlord.objects.get(clerk_user_id=clerk_user_id)
	except Landlord.DoesNotExist:
		return JsonResponse({'error': 'Landlord not found'}, status=404)

	today = date.today()
	current_month = today.replace(day=1)

	houses = []
	all_open_issues = []

	for house in landlord.houses.all().order_by('house_id'):
		house_data = {
			'house_id': house.house_id,
			'house_type': house.get_house_type_display(),
			'monthly_rent': str(house.monthly_rent),
			'deposit_amount': str(house.deposit_amount),
			'electricity_type': house.electricity_type,
			'is_occupied': house.is_occupied,
			'tenant': None,
			'open_issues': 0,
			'open_issues_list': [],
		}

		if house.is_occupied:
			try:
				tenant = house.current_tenant
				rent = Payment.objects.filter(
					tenant=tenant, month=current_month
				).first()
				water = WaterBill.objects.filter(
					tenant=tenant,
					date__month=today.month,
					date__year=today.year
				).first()
				elec = None
				if house.electricity_type == 'monthly':
					elec = ElectricityBill.objects.filter(
						tenant=tenant, month=current_month
					).first()

				open_requests = MaintenanceRequest.objects.filter(
					tenant=tenant, status='open'
				).order_by('created_at')

				house_data['tenant'] = {
					'full_name': tenant.full_name,
					'email': tenant.email,
					'phone_number': tenant.phone_number,
					'move_in_date': str(tenant.move_in_date),
					'household_members': [{'full_name': m.full_name, 'relationship': m.get_relationship_display()} for m in tenant.household_members.all()],
					'rent': {'amount': str(rent.amount), 'status': rent.status} if rent else None,
					'water': {'amount': str(water.amount), 'status': water.status} if water else None,
					'electricity': {'amount': str(elec.amount), 'status': elec.status} if elec else None,
				}

				issues_list = [
					{
						'category': req.get_category_display(),
						'description': req.description,
						'created_at': req.created_at.strftime('%Y-%m-%d'),
					}
					for req in open_requests
				]
				house_data['open_issues'] = len(issues_list)
				house_data['open_issues_list'] = issues_list

				for issue in issues_list:
					all_open_issues.append({
						'house_id': house.house_id,
						'tenant_name': tenant.full_name,
						'category': issue['category'],
						'description': issue['description'],
						'created_at': issue['created_at'],
					})

			except Exception:
				pass

		houses.append(house_data)

	all_open_issues.sort(key=lambda item: item['created_at'])

	return JsonResponse({
		'landlord_name': landlord.full_name,
		'profile': {
			'full_name': landlord.full_name,
			'email': landlord.email,
			'phone_number': landlord.phone_number,
			'created_at': str(landlord.created_at.date()),
		},
		'houses': houses,
		'all_open_issues': all_open_issues,
	})


def landlord_dashboard(request):
	return render(request, 'landlord_dashboard.html')


def houses_list(request):
	"""
	Public page showing available houses.
	No authentication required. QR code links here.
	"""
	available_houses = House.objects.filter(is_occupied=False).select_related('landlord')
	return render(request, 'houses_list.html', {'houses': available_houses})


def house_detail(request, house_id):
	"""
	Public detail page for one house.
	Shows the full photo gallery, video if uploaded, and full
	description. No authentication required, same as houses_list.
	"""
	house = get_object_or_404(House, house_id=house_id)
	gallery_photos = house.gallery_photos.all()
	return render(request, 'house_detail.html', {
		'house': house,
		'gallery_photos': gallery_photos,
	})


@csrf_exempt
@require_http_methods(["POST"])
def contact_message_api(request):
	"""
	Public contact form on the homepage. No authentication
	required, anyone reaches this. Saved straight to the database
	and read in Django admin, since there's no email server set
	up. is_tenant and house_number let Vanessa tell at a glance
	whether a message is from a current tenant or a stranger.
	"""
	try:
		body = json.loads(request.body)
		name = body.get('name', '').strip()
		email = body.get('email', '').strip()
		message = body.get('message', '').strip()
		is_tenant = bool(body.get('is_tenant', False))
		house_number = body.get('house_number', '').strip()

		if not name or not email or not message:
			return JsonResponse({'error': 'All fields are required'}, status=400)

		if len(message) < 5:
			return JsonResponse({'error': 'Message is too short'}, status=400)

		if is_tenant and not house_number:
			return JsonResponse({'error': 'Please add your house number'}, status=400)

		ContactMessage.objects.create(
			name=name,
			email=email,
			message=message,
			is_tenant=is_tenant,
			house_number=house_number if is_tenant else '',
		)
		return JsonResponse({'success': True})

	except Exception:
		return JsonResponse({'error': 'Server error'}, status=500)


def get_most_recent_tuesday(reference_date=None):
	"""
	Returns the most recent Tuesday on or before the given date,
	or today if no date is given. Water day is always Tuesday, so
	this gives a sensible default whichever day Vanessa happens
	to open the water entry screen.
	"""
	reference_date = reference_date or date.today()
	days_since_tuesday = (reference_date.weekday() - 1) % 7
	return reference_date - timedelta(days=days_since_tuesday)


def _parse_quantity(raw_value):
	"""
	Turns a form field's raw text into a safe non-negative int.
	Blank, missing, or garbage input all become 0 rather than
	raising an error and breaking the whole save.
	"""
	try:
		value = int(raw_value)
		return value if value > 0 else 0
	except (TypeError, ValueError):
		return 0


@staff_member_required
def admin_water_entry(request):
	"""
	Lets Vanessa enter the entire week's water round on one
	screen, one row per active tenant, instead of opening a
	separate Django admin form for each person every Tuesday.
	Saving creates, updates, or clears the WaterBill rows for
	whichever date is selected, defaulting to the most recent
	Tuesday.
	"""
	if request.method == 'POST':
		date_str = request.POST.get('entry_date')
		try:
			entry_date = date.fromisoformat(date_str)
		except (TypeError, ValueError):
			entry_date = get_most_recent_tuesday()

		tenants = Tenant.objects.filter(is_active=True, house__isnull=False)

		for tenant in tenants:
			qty_20 = _parse_quantity(request.POST.get(f'qty20_{tenant.id}', ''))
			qty_10 = _parse_quantity(request.POST.get(f'qty10_{tenant.id}', ''))
			is_paid = request.POST.get(f'paid_{tenant.id}') == 'on'
			status = 'paid' if is_paid else 'pending'
			date_paid = entry_date if is_paid else None

			if qty_20 > 0:
				WaterBill.objects.update_or_create(
					tenant=tenant, date=entry_date, jerrican_type='20L',
					defaults={
						'quantity': qty_20,
						'amount': qty_20 * 10,
						'status': status,
						'date_paid': date_paid,
					}
				)
			else:
				WaterBill.objects.filter(tenant=tenant, date=entry_date, jerrican_type='20L').delete()

			if qty_10 > 0:
				WaterBill.objects.update_or_create(
					tenant=tenant, date=entry_date, jerrican_type='10L',
					defaults={
						'quantity': qty_10,
						'amount': qty_10 * 5,
						'status': status,
						'date_paid': date_paid,
					}
				)
			else:
				WaterBill.objects.filter(tenant=tenant, date=entry_date, jerrican_type='10L').delete()

		messages.success(request, f"Water entries saved for {entry_date.strftime('%A, %d %B %Y')}.")
		return redirect(f"{reverse('admin_water_entry')}?date={entry_date.isoformat()}")

	date_param = request.GET.get('date')
	if date_param:
		try:
			entry_date = date.fromisoformat(date_param)
		except ValueError:
			entry_date = get_most_recent_tuesday()
	else:
		entry_date = get_most_recent_tuesday()

	tenants = Tenant.objects.filter(is_active=True, house__isnull=False).select_related('house').order_by('house__house_id')

	existing_bills = WaterBill.objects.filter(date=entry_date)
	existing_map = {}
	for bill in existing_bills:
		existing_map.setdefault(bill.tenant_id, {})[bill.jerrican_type] = bill

	rows = []
	for tenant in tenants:
		tenant_bills = existing_map.get(tenant.id, {})
		bill_20 = tenant_bills.get('20L')
		bill_10 = tenant_bills.get('10L')
		is_paid = True
		if tenant_bills:
			is_paid = all(b.status == 'paid' for b in tenant_bills.values())
		rows.append({
			'tenant': tenant,
			'qty_20': bill_20.quantity if bill_20 else '',
			'qty_10': bill_10.quantity if bill_10 else '',
			'is_paid': is_paid,
		})

	context = {
		'entry_date': entry_date,
		'rows': rows,
		'prev_date': entry_date - timedelta(days=7),
		'next_date': entry_date + timedelta(days=7),
	}
	return render(request, 'admin/water_entry.html', context)


@staff_member_required
def admin_overview(request):
	"""
	One screen showing what's actually due or open right now:
	rent not yet collected this month, who hasn't bought water
	this week, and every open maintenance issue. Reads live off
	the existing tables, nothing extra stored.
	"""
	today = date.today()
	current_month = today.replace(day=1)
	most_recent_tuesday = get_most_recent_tuesday()

	occupied_tenants = Tenant.objects.filter(is_active=True, house__isnull=False).select_related('house')

	rent_rows = []
	for tenant in occupied_tenants:
		payment = Payment.objects.filter(tenant=tenant, month=current_month).first()
		rent_rows.append({
			'tenant': tenant,
			'house_id': tenant.house.house_id,
			'amount': payment.amount if payment else tenant.house.monthly_rent,
			'status': payment.status if payment else 'not entered',
		})

	pending_rent = [r for r in rent_rows if r['status'] in ('pending', 'overdue', 'not entered')]

	paid_tenant_ids_this_week = set(
		WaterBill.objects.filter(date=most_recent_tuesday).values_list('tenant_id', flat=True)
	)
	not_bought_water = []
	for tenant in occupied_tenants:
		if tenant.id not in paid_tenant_ids_this_week:
			not_bought_water.append({
				'tenant': tenant,
				'house_id': tenant.house.house_id,
			})

	open_issues = MaintenanceRequest.objects.filter(status='open').select_related('tenant', 'tenant__house').order_by('created_at')

	context = {
		'today': today,
		'most_recent_tuesday': most_recent_tuesday,
		'pending_rent': pending_rent,
		'total_occupied': occupied_tenants.count(),
		'not_bought_water': not_bought_water,
		'open_issues': open_issues,
	}
	return render(request, 'admin/overview.html', context)