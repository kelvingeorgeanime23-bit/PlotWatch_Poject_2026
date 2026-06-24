from django.db import models

# Create your models here.

# LANDLORD MODEL: Each landlord gets one profile.
class Landlord(models.Model):
	clerk_user_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
	full_name = models.CharField(max_length=100)
	phone_number = models.CharField(max_length=20)
	email = models.EmailField()
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.full_name


# HOUSE MODEL: Each house belongs to one landlord and has a unique id eg D4, G5, M1.
class House(models.Model):
	HOUSE_TYPE_CHOICES = [
		('single_room', 'Single Room'),
		('bedsitter', 'Bedsitter'),
		('one_bedroom', 'One Bedroom'),
		('two_bedroom', 'Two Bedroom'),
	]

	ELECTRICITY_CHOICES = [
		('token', 'Token Meter'),
		('monthly', 'Monthly Bill'),
	]

	landlord = models.ForeignKey(
		Landlord,
		on_delete=models.CASCADE,
		related_name='houses'
	)
	house_id = models.CharField(max_length=10, unique=True)
	house_type = models.CharField(max_length=20, choices=HOUSE_TYPE_CHOICES)
	monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
	deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
	electricity_type = models.CharField(max_length=10, choices=ELECTRICITY_CHOICES)
	is_occupied = models.BooleanField(default=False)
	description = models.TextField(blank=True)
	photo = models.ImageField(upload_to='house_photos/', blank=True, null=True)
	video = models.FileField(upload_to='house_videos/', blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"House {self.house_id} ({self.get_house_type_display()})"


# HOUSE PHOTO MODEL: Extra gallery photos for a house's detail page.
# The single `photo` field above stays as the cover photo on the list
# page, kept lightweight on purpose. This model holds the rest.
class HousePhoto(models.Model):
	house = models.ForeignKey(
		House,
		on_delete=models.CASCADE,
		related_name='gallery_photos'
	)
	image = models.ImageField(upload_to='house_photos/gallery/')
	order = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['order', 'created_at']

	def __str__(self):
		return f"Photo for House {self.house.house_id}"


# TENANT MODEL: Each tenant is linked to a house.
class Tenant(models.Model):
	clerk_user_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
	house = models.OneToOneField(
		House,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='current_tenant'
	)
	full_name = models.CharField(max_length=100)
	date_of_birth = models.DateField()
	id_number = models.CharField(max_length=20, unique=True)
	phone_number = models.CharField(max_length=20)
	email = models.EmailField()
	emergency_contact_name = models.CharField(max_length=100, blank=True)
	emergency_contact_phone = models.CharField(max_length=20, blank=True)
	move_in_date = models.DateField()
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.full_name} - House {self.house.house_id if self.house else 'Unassigned'}"


# PAYMENT MODEL: Admin manually enters all pending, paid and overdue payments (Rent).
class Payment(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('paid', 'Paid'),
		('overdue', 'Overdue'),
	]

	tenant = models.ForeignKey(
		Tenant,
		on_delete=models.CASCADE,
		related_name='payments'
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	month = models.DateField()
	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
	date_paid = models.DateField(null=True, blank=True)
	mpesa_reference = models.CharField(max_length=50, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.tenant.full_name} - Rent {self.month.strftime('%B %Y')} - {self.status}"


# WATERBILL MODEL: Admin tracks jerrican water payments per tenant, enters manually every Tuesday.
class WaterBill(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('paid', 'Paid'),
	]

	JERRICAN_CHOICES = [
		('20L', '20 Litre - KSh 10'),
		('10L', '10 Litre - KSh 5'),
	]

	tenant = models.ForeignKey(
		Tenant,
		on_delete=models.CASCADE,
		related_name='water_bills'
	)
	date = models.DateField()
	jerrican_type = models.CharField(max_length=5, choices=JERRICAN_CHOICES)
	quantity = models.PositiveIntegerField(default=1)
	amount = models.DecimalField(max_digits=8, decimal_places=2)
	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
	date_paid = models.DateField(null=True, blank=True)
	mpesa_reference = models.CharField(max_length=50, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.tenant.full_name} - Water {self.date} - {self.status}"


# ELECTRICITY BILL MODEL: Admin enters manually each month for houses that do not use tokens.
class ElectricityBill(models.Model):
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('paid', 'Paid'),
		('overdue', 'Overdue'),
	]

	tenant = models.ForeignKey(
		Tenant,
		on_delete=models.CASCADE,
		related_name='electricity_bills'
	)
	month = models.DateField()
	units_used = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
	date_paid = models.DateField(null=True, blank=True)
	mpesa_reference = models.CharField(max_length=50, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.tenant.full_name} - Electricity {self.month.strftime('%B %Y')} - {self.status}"


# MAINTENANCE REQUEST MODEL: Tenant raises an issue, goes to admin (caretaker) only.
class MaintenanceRequest(models.Model):
	STATUS_CHOICES = [
		('open', 'Open'),
		('in_progress', 'In Progress'),
		('resolved', 'Resolved'),
	]

	CATEGORY_CHOICES = [
		('roof', 'Roof Leak'),
		('plumbing', 'Plumbing'),
		('electrical', 'Electrical'),
		('door', 'Door or Lock'),
		('window', 'Window'),
		('other', 'Other'),
	]

	tenant = models.ForeignKey(
		Tenant,
		on_delete=models.CASCADE,
		related_name='maintenance_requests'
	)
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
	description = models.TextField()
	status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
	admin_notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.tenant.full_name} - {self.get_category_display()} - {self.status}"


# CONTACT MESSAGE MODEL: Public contact form on the homepage.
# No authentication, anyone can send one. No email server is set
# up, so this is the simple version: saved here, read by Vanessa
# or Kelvin in Django admin, same trust level as the rest of the
# site's manual workflows. is_tenant and house_number let a
# tenant flag themselves, since otherwise there's no way to tell
# a tenant's message apart from a stranger's just from an email
# address.
class ContactMessage(models.Model):
	name = models.CharField(max_length=100)
	email = models.EmailField()
	message = models.TextField()
	is_tenant = models.BooleanField(default=False)
	house_number = models.CharField(max_length=10, blank=True, default='')
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.name} - {self.created_at.strftime('%Y-%m-%d')}"