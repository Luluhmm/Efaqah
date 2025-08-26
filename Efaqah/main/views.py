from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.models import User, Group
from django.contrib.auth import login , authenticate, logout
from django.contrib import messages
from .forms import RegistrationForm
from .models import Registration, Hospital, staffProfile
from django.conf import settings
from django.core.mail import send_mail , EmailMessage
import uuid
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.urls import reverse_lazy
from django.urls import reverse
from django.contrib.auth.hashers import make_password
import secrets
from django.utils import timezone
from cities_light.models import Country, City





# Create your views here.
#------------------------------------------------------------------------------------------------------

def user_login(request):
    payment_status = request.GET.get('payment')
    hospital_id = request.GET.get('hospital_id')

    if payment_status == 'success' and hospital_id:
        hospital = get_object_or_404(Hospital, id=hospital_id)
        

        if not hasattr(hospital, 'manager') or hospital.manager is None:

            manager_username = request.session.get('manager_username')
            manager_password = request.session.get('manager_password')
            manager_email = request.session.get('manager_email')
            first_name = request.session.get('first_name')
            last_name = request.session.get('last_name')


            user = User.objects.create_user(
                username=manager_username,
                password=manager_password,
                email=manager_email,
                first_name=first_name,
                last_name=last_name
            )


            staffProfile.objects.create(
                user=user,
                hospital=hospital,
                role='manager'
            )


            manager_group, created = Group.objects.get_or_create(name='Manager')
            user.groups.add(manager_group)

            hospital.manager = user
            hospital.activate_subscription(plan_year=1)


            del request.session['manager_username']
            del request.session['manager_password']
            del request.session['manager_email']
            del request.session['first_name']
            del request.session['last_name']
            del request.session['hospital_id']

            messages.success(request, f"Your hospital subscription is complete! Your account is created. You can now log in.")

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.groups.filter(name="Doctor").exists():
                return redirect("doctor:doctor_dashboard")
            
            elif user.groups.filter(name="Nurse").exists():
                return redirect("nurse:nurse_dashboard")
            
            elif user.groups.filter(name="Manager").exists():
                return redirect("manager:manager_dashboard")
            
            else:
                messages.error(request, "Invalid username or password", "alert-danger")

        return redirect("main:login")
    
    
    return render(request, "main/login.html")

#------------------------------------------------------------------------------------------------------

def landing_page(request):
    return render(request, "main/landing_page.html")

#------------------------------------------------------------------------------------------------------

def request_form(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            if Registration.objects.filter(email=email).exists():
                messages.error(request, "This email has already been used for a demo request.")
                return redirect("main:request_form")

            registration = form.save() #saving the user info

            subject = "New Registration Form Submission"
            message = f"""
            <html>
                <body>
                    <h2>New Registration Form Submission</h2>
                    <p><strong>First Name</strong>: {registration.firstname}</p>
                    <p><strong>Last Name</strong>: {registration.lastname}</p>
                    <p><strong>Email</strong>: {registration.email}</p>
                    <p><strong>Phone</strong>: {registration.phone}</p>
                    <p><strong>Medical Affiliation</strong>: {registration.medical_affiliation}</p>
                    <p><strong>Description</strong>: {registration.description}</p>
                </body>
            </html>
            """

            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                reply_to=[registration.email],
            )
            email.content_subtype = "html"
            email.send()

            


            user_subject = "Your Registration was Successful"
            user_message = f"""
                <html>
                    <body>
                        <p>Hi {registration.firstname},</p>
                        <p>Your message has been submitted successfully. We'll reply to you soon.</p>
                        <p>Thank you for reaching out!</p>
                    </body>
                </html>
            """
            user_email = EmailMessage(
                user_subject,
                user_message,
                settings.DEFAULT_FROM_EMAIL,
                [registration.email],
            )
            user_email.content_subtype = "html"
            user_email.send()

            messages.success(request, "Form submitted successfully. We'll contact you soon.")
            return redirect("main:login")
    else:
        form = RegistrationForm()

    return render(request, "main/request_form.html", {"form":form})

#------------------------------------------------------------------------------------------------------

def create_user_and_send_credentials(registration):
    """A helper function to create the user and send the email."""
    email = registration.email

    
    #Generate a unique username
    username = f"{registration.firstname.lower()}_{uuid.uuid4().hex[:6]}"
    
    #Generate a random password
    password = secrets.token_urlsafe(10)

    #Create the new user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=registration.firstname,
        last_name=registration.lastname
    )

    registration.user = user
    registration.save()

    #Assign the user to the 'demo' group
    demo_group, created = Group.objects.get_or_create(name='demo')
    user.groups.add(demo_group)

    #Send the welcome email with credentials
    subject = "Your New Account Details"
    message = f"""
    <html>
        <body>
            <p>Hello {user.first_name},</p>
            <p>Thank you for your payment. Your account has been created.</p>
            <p>You can now log in using these credentials:</p>
            <p><strong>Username:</strong> {username}<br>
               <strong>Password:</strong> {password}</p>
            <p>Please log in at: <a href="http://127.0.0.1:8000/login/">Login</a></p>
            <p>Regards,<br>Efaqah</p>
        </body>
    </html>
    """
    email_msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
    email_msg.content_subtype = "html"
    email_msg.send()

"""
@csrf_exempt # Stripe does not send a CSRF token
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        registration_id = session.get('metadata', {}).get('registration_id')

        if registration_id:
            try:
                registration = Registration.objects.get(id=registration_id)
                if registration.status != 'paid':
                    registration.status = 'paid'
                    registration.save()
                    try:
                        create_user_and_send_credentials(registration)
                    except Exception as e:
                        print("Error in create_user_and_send_credentials:", e)
            except Registration.DoesNotExist:
                print(f"Registration with ID {registration_id} not found.")

    return HttpResponse(status=200) # Let Stripe know we received it
"""

#------------------------------------------------------------------------------------------------------

def send_payment_link_email(request, registration):

    stripe.api_key = settings.STRIPE_SECRET_KEY

    success_url = request.build_absolute_uri(reverse('main:payment_success') + f"?registration_id={registration.id}")
    cancel_url = request.build_absolute_uri(reverse('main:payment_cancelled'))

    try:
        session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': "Demo Access Fee",
                            },
                            'unit_amount': 2000, #This is $20.00
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url = success_url,
                    cancel_url = cancel_url,
                    metadata = {
                        'registration_id': str(registration.id)
                    } # This is going to pass the registration id so we know who paid
        )

        registration.stripe_session_id = session.id
        registration.save()

        registration.payment_link = session.url

        subject = "Your Payment Link for Demo Access"
        message = f"""
                Hello {registration.firstname},

                Your request has been approved! Please complete the payment to create your account.

                Click here to pay: {registration.payment_link}

                Thank you,
                Efaqah
                """
        send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [registration.email], # Send to the user who registered
                    fail_silently=False,
                )
        return True

    except Exception as e:
        print(f"Error creating Stripe session: {e}")
        return False
#------------------------------------------------------------------------------------------------------

def subscribe_view(request):
    return render(request,"main/subscribe_page.html")

#------------------------------------------------------------------------------------------------------

def subscribe_form(request):
    plan = request.GET.get("plan")
    countries = Country.objects.all().order_by('name')
    if request.method == "POST":
        hospital_name = request.POST.get('hospital_name')
        country = request.POST.get('country')
        city_id = request.POST.get('city')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        plan = request.POST.get('plan')
        manager_user = request.POST.get('manager_username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        manager_email = request.POST.get('manager_email')
        password = request.POST.get('password')


        city_instance = None
        if city_id:
            try:
                city_instance = City.objects.get(id=city_id)
            except City.DoesNotExist:
                messages.error(request,"Selected city does not exist.")
                return redirect("main:subscribe_form")

        active_hospital = Hospital.objects.filter(name__iexact=hospital_name, subscription_status="paid", subscription_end_date__gt=timezone.now().date()).first()

        if active_hospital:
            messages.error(request, "This hospital already has an active subscription.")
            return redirect("main:subscribe_form")


        active_email = Hospital.objects.filter(
            contact_email__iexact=manager_email,
            subscription_status="paid",
            subscription_end_date__gt=timezone.now()
        ).first()

        if active_email:
            messages.error(request, "This email is already associated with an active subscription.")
            return redirect("main:subscribe_form")

        request.session['manager_username'] = manager_user
        request.session['manager_password'] = password
        request.session['manager_email'] = manager_email
        request.session['first_name'] = first_name
        request.session['last_name'] = last_name

        plan_map = {
            "499": "basic",
            "999": "pro",
            "1999": "enterprise",
        }

        hospital_plan = plan_map.get(plan, "basic")

        hospital = Hospital.objects.create(
            name=hospital_name,
            country=country,
            city=city_instance,
            address=address,
            contact_email=manager_email,
            contact_phone=phone,
            plan=hospital_plan,
            subscription_status='pending'
        )
        

        request.session['hospital_id'] = hospital.id

        return redirect("main:create_checkout_session", plan=plan, hospital_id=hospital.id)
    
    return render(request, 'main/subscribe_form.html', {"plan": plan, "countries":countries})
    

#------------------------------------------------------------------------------------------------------

def payment_success(request):
    registration_id = request.GET.get("registration_id")
    if registration_id:
        try:
            registration = Registration.objects.get(id=registration_id)
            if registration.status != "paid":
                registration.status = "paid"
                registration.save()
                create_user_and_send_credentials(registration)
        except Registration.DoesNotExist:
            messages.error(request, "Registration not found.")
    return render(request, "main/payment_success.html")


#------------------------------------------------------------------------------------------------------

def payment_cancelled(request):
    return render(request, "main/cancelled.html")

#------------------------------------------------------------------------------------------------------

def payment_pending(request):
    return render(request, "main/payment_pending.html")
    
def create_checkout_session(request, plan, hospital_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    hospital_id = request.session.get('hospital_id')
    if not hospital_id:
        messages.error(request, "Hospital registration data not found.")
        return redirect("main:subscribe_form")

    hospital = get_object_or_404(Hospital, id=hospital_id)

    price_map = {
        "499": 49900,
        "999": 99900,
        "1999": 199900,
    }

    if plan not in price_map:
        return JsonResponse({"error":"Invalid plan"}, status=400)
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"{plan} Plan Subscription",
                },
                'unit_amount': price_map[plan],
            },
            "quantity": 1,
        }],
        mode='payment',

        success_url=request.build_absolute_uri(reverse('main:login') + f"?payment=success&hospital_id={hospital.id}"),
        cancel_url=request.build_absolute_uri(reverse('main:payment_cancelled')),
    )

    return redirect(session.url, code=303)

#------------------------------------------------------------------------------------------------------

def logout_view(request):
    logout(request)
    return render(request, "main/landing_page.html")


#------------------------------------------------------------------------------------------------------

def get_cities(request, country_id):
    cities = City.objects.filter(country_id=country_id).order_by('name')
    city_list = [{'id': c.id, 'name': c.name} for c in cities]
    return JsonResponse({'cities': city_list})