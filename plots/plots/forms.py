from django import forms
from django.utils import timezone
from .models import Booking

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["house" , "check_in" , "check_out"]
        labels = {"house" : "Apartment"}
        widgets = {
            "house" : forms.Select(attrs={"class" : "form_select"}),
            "check_in" : forms.DateInput(attrs={"type" : "date" , "class" : "form-control"}),
            "check_out" : forms.DateInput(attrs={"type" : "date" , "class" : "form-control"}),
        }

    def clean(self):
        data = super().clean() 
        house,cin,cout = data.get("house") , data.get("check_in") , data.get("check_out")
        if house and cin and cout :
            if cin < timezone.localdate():
                raise forms.ValidationError("Check-in cant be in the past.") 
            if cout <= cin:
                raise forms.ValidationError("Check-out must be after the check-in") 
            if not house.is_free(cin, cout):
                raise forms.ValidationError("Sorry, that appartmetn is alreaty booked")
        return data  
        
          