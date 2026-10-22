from django import forms


class BookingForm(forms.Form):
    house = forms.ChoiceField(label="Apartment")
    check_in = forms.DateField(
        label="Check-in",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    check_out = forms.DateField(
        label="Check-out",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, houses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["house"].choices = [
            (str(house["id"]), f'{house["name"]} — ${house["price_per_night"]}/night')
            for house in houses
        ]

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        if check_in and check_out and check_out <= check_in:
            self.add_error("check_out", "Check-out must be after check-in.")
        return cleaned_data


class ReviewForm(forms.Form):
    rating = forms.ChoiceField(
        choices=[(value, f"{value} star{'s' if value != 1 else ''}") for value in range(1, 6)],
    )
    comment = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
