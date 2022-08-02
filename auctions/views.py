from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django import forms

from .models import *

choices = [('fashion', 'Fashion'), ('electronics', 'Electronics'), ('home', 'Home'), ('other', 'Other')]

class ListingForm(forms.Form):
    title = forms.CharField(label="Title: ", max_length=64, widget=forms.TextInput(attrs={'placeholder': 'Title'}))
    bid = forms.DecimalField(label="Bid: ", max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': 'Bid'}))
    category = forms.ChoiceField(label="Category", choices=choices, required=False)
    description = forms.CharField(label="Description: ", widget=forms.Textarea(attrs={'placeholder': 'Description'}))
    image_url = forms.CharField(label="Image URL: ", max_length=250, required=False, widget=forms.TextInput(attrs={'placeholder': 'Image URL'}))

class BidForm(forms.Form):
    bid = forms.DecimalField(max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': 'Bid'}))

def index(request):
    return render(request, "auctions/index.html", {
        "listings": Listing.objects.filter(active=True)
    })

def categories(request):
    return render(request, "auctions/categories.html")

def filter_categories(request, category):
    return render(request, "auctions/index.html", {
        "listings": Listing.objects.filter(category=category, active=True)
    })


@login_required
def create_listing(request):
    if request.method == "POST":
        new_listing_form = ListingForm(request.POST)
        if new_listing_form.is_valid():
            new_listing = Listing(
                title=new_listing_form.cleaned_data["title"], 
                bid=new_listing_form.cleaned_data["bid"], 
                description=new_listing_form.cleaned_data["description"],
                category=new_listing_form.cleaned_data["category"], 
                image_url=new_listing_form.cleaned_data["image_url"],
                user=request.user
                )
            new_listing.save()
        return HttpResponseRedirect(reverse("index"))
        
    return render(request, "auctions/create_listing.html", {
        "form": ListingForm()
    })

@login_required
def close_listing(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    if listing.user == request.user:
        listing.active = False
        listing.save()
    return HttpResponseRedirect(f"/view/{listing_id}")

@login_required
def watchlist(request):
    return render(request, "auctions/watchlist.html", {
        "watchlists": Watchlist.objects.filter(user=request.user)
    })

@login_required
def add_watchlist(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    if listing.watchlists.filter(user=request.user).exists():
        listing.watchlists.filter(user=request.user).delete()
    else:
        wlist = Watchlist(listing=listing, user=request.user)
        wlist.save()
    return HttpResponseRedirect(f"/view/{listing_id}")

@login_required
def comment(request, listing_id):
    if request.method == "POST":
        listing = Listing.objects.get(pk=listing_id)
        content = request.POST["content"]
        comment = Comment(listing=listing, user=request.user, content=content)
        comment.save()
    return HttpResponseRedirect(f"/view/{listing_id}")

def view_listing(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    try:
        watchlisted = listing.watchlists.filter(user=request.user)
    except TypeError:
        watchlisted = False
        
    if request.method == "POST":
        new_bid_form = BidForm(request.POST)
        if new_bid_form.is_valid():
            bid_amt = new_bid_form.cleaned_data["bid"]
            highest_bid_obj = listing.bids.last()

            if highest_bid_obj:
                highest_bid = highest_bid_obj.bid
            else:
                highest_bid = -1

            if bid_amt >= listing.bid and bid_amt > highest_bid:
                new_bid = Bid(bid=bid_amt, listing=listing, user=request.user)
                new_bid.save()
                listing.bid = bid_amt
                listing.save()
                return render(request, "auctions/view_listing.html", {
                    "listing": listing,
                    "form": BidForm(),
                    "bids": listing.bids.all(),
                    "highest_bid": listing.bids.last(),
                    "err": False,
                    "watchlisted": watchlisted,
                    "creator": listing.user == request.user,
                    "comments": listing.comments.all()
                })

        return render(request, "auctions/view_listing.html", {
                    "listing": listing,
                    "form": new_bid_form,
                    "bids": listing.bids.all(),
                    "highest_bid": listing.bids.last(),
                    "err": True,
                    "watchlisted": watchlisted,
                    "creator": listing.user == request.user,
                    "comments": listing.comments.all()
                })

    return render(request, "auctions/view_listing.html", {
        "listing": listing,
        "form": BidForm(),
        "bids": listing.bids.all(),
        "highest_bid": listing.bids.last(),
        "err": False,
        "watchlisted": watchlisted,
        "creator": listing.user == request.user,
        "comments": listing.comments.all()
    })

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")
