from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import *

from apps.accounts.models import *
from apps.accounts.serializers import *
from apps.accounts.permissions import *
from core.utils.emails import send_welcome_email
# Create your views here.


class RegistrationView(APIView):

    def post(self, request):
       
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            send_welcome_email(user)
            return Response({ "success": True, "message": "Registration successful" }, status=status.HTTP_200_OK)
        return Response({ "success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):

    def post(self, request):
        
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            return Response({ "success": True, "message": serializer.validated_data}, status=status.HTTP_200_OK)
        return Response({ "success": False, "message": serializer.errors }, status=status.HTTP_400_BAD_REQUEST)






class OfficeView(generics.ListAPIView):
    serializer_class = OfficeSerializer
    queryset = Office.objects.all().order_by("name")



class CouriersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()


    def get_queryset(self):
        queryset = self.queryset.filter(Q(role="driver") | Q(role="partner_rider")).order_by("full_name")
        return queryset




class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"success": False, "message": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"success": False, "message": "If that email exists, a reset link has been sent."}, status=status.HTTP_200_OK)


        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))


        reset_url = f"https://app.expa.co.ke/auth/reset-password?uid={uid}&token={token}" 
        send_mail(
            "Password Reset",
            f"Clivk the link to reset your password: {reset_url}",
            "",
            [user.email],
            fail_silently=False,
        )
        return Response({ "success": True, "message": "Password reset link sent."}, status=status.HTTP_200_OK)



class PasswordResetConfirmView(APIView):
    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")

        if not all([uidb64, token, password]):
            return Response({"success": False, "message": "Missing fields."}, status=status.HTTP_400_BAD_REQUEST)
        

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({"success": False, "message": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)


        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            return Response({"success": False, "message": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()

        return Response({"success": True, "message": "Password reset successfully."}, status=status.HTTP_200_OK)



class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user






