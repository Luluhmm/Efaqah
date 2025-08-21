from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.models import User, Group
from django.contrib.auth import login , authenticate
from django.contrib import messages
from .forms import RegistrationForm
from .models import Registration
from django.conf import settings
from django.core.mail import send_mail , EmailMessage
import uuid
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.urls import reverse_lazy
from django.urls import reverse



# Create your views here.

def user_login(request):
    if request.GET.get('status') == 'success':
        messages.success(request, "Payment successful! Your account has been created. Please check your email for your login credentials.")
    elif request.GET.get('status') == 'cancelled':
        messages.warning(request, "Your payment was cancelled. You can try again from the payment link in your email.")

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
            
            else:
                messages.error(request, "Invalid username or password", "alert-danger")

        return redirect("main:login")
    
    
    return render(request, "main/login.html")



def landing_page(request):
    return render(request, "main/landing_page.html")

def request_form(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
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


def create_user_and_send_credentials(registration):
    """A helper function to create the user and send the email."""
    email = registration.email
    
    # 1. Generate a unique username
    username = f"{registration.firstname.lower()}_{uuid.uuid4().hex[:6]}"
    
    # 2. Generate a random password
    password = User.objects.make_random_password()

    # 3. Create the new user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=registration.firstname,
        last_name=registration.lastname
    )

    # 4. Assign the user to the 'demo' group
    demo_group, created = Group.objects.get_or_create(name='demo')
    user.groups.add(demo_group)

    # 5. Send the welcome email with credentials
    subject = "Your New Account Details"
    message = f"""
    Hello {user.first_name},

    Thank you for your payment. Your account has been created.
    You can now log in using these credentials:

    Username: {username}
    Password: {password}

    Please log in at: https://*.ngrok-free.app/login/

    Regards,
    The Team
    """
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])

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
                    # This is the magic moment!
                    create_user_and_send_credentials(registration)
            except Registration.DoesNotExist:
                print(f"Registration with ID {registration_id} not found.")

    return HttpResponse(status=200) # Let Stripe know we received it


def send_payment_link_email(request, registration):

    stripe.api_key = settings.STRIPE_SECRET_KEY

    success_url = request.build_absolute_uri(reverse('main:login')) + '?status=success'
    cancel_url = request.build_absolute_uri(reverse('main:login')) + '?status=cancelled'

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
                        'registration_id': registration.id
                    } # This is going to pass the registration id so we know who paid
        )

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

