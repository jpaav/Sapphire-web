from django.db import models
from django.db.models import Q
from datetime import datetime, timedelta, timezone

from django.contrib.auth.models import User, UserManager
from accounts.models import Profile
from groups.models import Group
import ast
from collections import OrderedDict
import json
import pytz

"""
Notes:
I have used models.CASCADE in all the db relationship on_delete cases. I do not
know if this is good practice or will result in errors later down the line.
"""

"""
A slot object allows volunteers to sign up for it and has a start time and end
time. It has a parent Event.
"""


class Slot(models.Model):
    def __str__(self):
        return 'Slot: ' + self.title
    objects = models.Manager()
    # TODO make sure this can only point to one Event and not more than that
    parentEvent = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
        null=True
    )
    parentGroup = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=True
    )
    start = models.DateTimeField()
    end = models.DateTimeField()

    # The minimun number of volunteers this slot needs to have. Set by Event
    # organizer and factored into slot priority
    minVolunteers = models.IntegerField(blank=True, null=True)
    # The maximum number of volunteers this slot can have. Set by Event
    # organizer and stops too many Profiles from signing up
    maxVolunteers = models.IntegerField(blank=True, null=True)
    # TODO allow a getPriority() function to get the instantanious priority of
    # the Event object

    title = models.CharField(max_length=240)
    # The String descriptionof the event
    description = models.CharField(max_length=960, blank=True, null=True)

    # The String location Name of the Event
    location = models.CharField(max_length=240, blank=True, null=True)
    # The String address of the Event
    address = models.CharField(max_length=240, blank=True, null=True)
    # The String city of the Event'
    city = models.CharField(max_length=240, blank=True, null=True)
    # The String state of event
    # TODO: This should be restored to 2 if that was not an accident
    state = models.CharField(max_length=200, blank=True, null=True)
    # The Integer zip code of the Event
    zip_code = models.IntegerField(blank=True, null=True)

    paymentPerHour = models.DecimalField(blank=True, null=True, default=0, max_digits=5, decimal_places=2)

    extraFields = models.CharField(max_length=255, blank=True, null=True)

    private = models.BooleanField(blank=False, null=False, default=False)

    def is_payment_nonzero(self):
        return self.paymentPerHour != 0

    def is_volunteered(self, user):
        return User_Slot.objects.filter(parentSlot=self, volunteer=user).first() != None


    def getNumberUserSlotsTotal(self):
        return len(User_Slot.objects.filter(parentSlot=self))

    def getNumberUserSlotsFilled(self):
        return len(User_Slot.objects.filter(parentSlot=self).exclude(volunteer=None))

    def get_users_groups_slots(user):
        groups = Group.get_is_member_list(user)
        events = None
        slots = None
        for group in groups:
            if (events == None):
                events = Event.objects.filter(parentGroup=group)
            else:
                groups_events = Event.objects.filter(parentGroup=group)
                events = events | groups_events

            if (slots == None):
                slots = Slot.objects.filter(parentGroup=group)
            else:
                groups_slots = Slot.objects.filter(parentGroup=group)
                slots = slots | groups_slots

        if events == None:
            return None

        for event in events:
            if (slots == None):
                slots = Slot.objects.filter(parentEvent=event)
            else:
                events_slots = Slot.objects.filter(parentEvent=event)
                slots = slots | events_slots


        if (slots == None):
            return slots
        return slots.order_by(
            'start')  # Slot.objects.filter(Q(parentEvent.parentGroup.get_is_member(user))).objects.order_by('start')

    def get_extra(self):
        if (self.extraFields != None):
            return self.extraFields.split(',')


    def get_group(self):
        if self.parentEvent is not None:
            group = self.parentEvent.parentGroup
        else:
            group = self.parentGroup

        return group


class User_Slot(models.Model):
    def __str__(self):
        return 'User_Slot: ' + self.parentSlot.title
    volunteer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    parentSlot = models.ForeignKey(
        Slot,
        on_delete=models.CASCADE,
        null=False,
    )

    signin = models.DateTimeField(blank=True, null=True)
    signout = models.DateTimeField(blank=True, null=True)

    def is_signin_null(self):
        return self.signin == None

    def is_signout_null(self):
        return self.signout == None

    def is_volunteer_null(self):
        return self.volunteer == None

    difference = models.CharField(blank=True, max_length=100, null=True)

    payment = models.DecimalField(blank=True, null=False, default=0, max_digits=10, decimal_places=2)

    extraFields = models.CharField(blank=True, max_length=240, null=True)

    def getExtraFieldValues(self):
        efs = json.loads(self.extraFields)
        return [val for key,val in efs.items()]


    accepted = models.CharField(blank=True, max_length=240, default="No")

    value = None  # this is used to export the extra fields to html


    def updateDeltaTimes(self):
        if (self.signin != None and self.signout != None):
            signout, signin = self.signout, self.signin
            print(signout, signin)
            # import pdb; pdb.set_trace() 

            deltaTime = signout - signin
            seconds = deltaTime.seconds

            
            self.difference = str(timedelta(seconds=seconds))
            self.payment = (seconds/60/60) * (float(self.parentSlot.paymentPerHour))

            self.save()

    def getUserSlots(group):
        events = Event.objects.filter(parentGroup=group)
        slots = Slot.objects.filter(parentGroup=group)

        for event in events:
            if (slots == None):
                slots = Slot.objects.filter(parentEvent=event)

            else:
                slots = slots | Slot.objects.filter(parentEvent=event)

        user_slots = None

        for slot in slots:
            if (user_slots == None):
                user_slots = User_Slot.objects.filter(parentSlot=slot)

            else:
                user_slots = user_slots | User_Slot.objects.filter(parentSlot=slot)

        return user_slots

    def get_extra(self):
        ans = json.loads(self.extraFields.replace('\'', '\"'), object_pairs_hook=OrderedDict)
        if type(ans) is type([]):
            return {}
        return ans

    def save_extra(self, newList):
        self.extraFields = json.dumps(newList)

    def set_extra(self, field, newVal):
        a = self.get_extra()
        a[field] = newVal
        self.save_extra(a)

    def remove_extra(self, field):
        self.extraFields = self.get_extra()
        del self.extraFields[field]

    def prep_html(self):
        print(self.get_extra(), type(self.get_extra()))
        self.value = list(self.get_extra().items())


class Event(models.Model):
    def __str__(self):
        return 'Event: ' + self.name
    parentGroup = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        null=False,
    )
    is_single = models.BooleanField(default=False)
    # type = models.CharField(max_length=80)
    objects = models.Manager()
    # The organizer of the Event
    organizer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False
    )
    # The string name of the Event
    name = models.CharField(max_length=80)
    # The String descriptionof the event
    description = models.CharField(blank=True, max_length=960)

    # The String location Name of the Event
    location = models.CharField(blank=True, max_length=240)
    # The String address of the Event
    address = models.CharField(blank=True, max_length=240)
    # The String city of the Event'
    city = models.CharField(blank=True, max_length=240)
    # The String state of event
    state = models.CharField(blank=True, max_length=200)
    # type = models.CharField(max_length=30)
    # The Integer zip code of the Event
    zip_code = models.IntegerField(blank=True, null=True)

    slots = models.ForeignKey(
        Slot,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="slot_set"
    )
    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)

    private = models.BooleanField(blank=False, null=False, default=False)

    # The minimun number of volunteers this slot needs to have. Set by Event
    # organizer and factored into slot priority
    # minVolunteers = models.IntegerField(null=True)
    # The maximum number of volunteers this slot can have. Set by Event
    # organizer and stops too many Profiles from signing up
    # maxVolunteers = models.IntegerField(null=True)
    # TODO allow a getPriority() function to get the instantanious priority of
    # the Event object
    # in_person = models.NullBooleanField(null=True)
    # A one to many relationship holding the Slots for an Event object

    # RAISING ERRORS

    # slots = models.ForeignKey(
    #     'Slot',
    #     on_delete=models.CASCADE,
    #     null=True,
    #     blank=True
    # )
    def get_in_person(self):
        if self.in_person:
            return 'Yes'
        return 'No'

    def get_users_groups_events(user):
        groups = Group.get_is_member_list(user)
        events = None
        for group in groups:
            if (events == None):
                events = Event.objects.filter(parentGroup=group)
            else:
                groups_events = Event.objects.filter(parentGroup=group)
                events = events.union(groups_events)

        if (events == None):
            return events
        return events.order_by('start')
