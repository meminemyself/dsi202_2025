from django.db import models
from django.contrib.auth.models import User

class Equipment(models.Model):
    name = models.CharField(max_length=200)
    price = models.FloatField()
    image_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Tree(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)
    description = models.TextField()
    is_recommended = models.BooleanField(default=False)
    average_rating = models.FloatField(default=4.5)
    review_count = models.PositiveIntegerField(default=0)
    tags = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

class PlantingLocation(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location_type = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class UserPlanting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE)
    location = models.ForeignKey(PlantingLocation, on_delete=models.CASCADE)
    planting_date = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} planted {self.tree.name} at {self.location.name}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    notification_date = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username} on {self.notification_date.date()}"

class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.user.username} purchased {self.equipment.name} (x{self.quantity})"

class NewsArticle(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image_url = models.URLField()
    article_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    class Purchase(models.Model):
        user = models.ForeignKey(User, on_delete=models.CASCADE)
        equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
        quantity = models.PositiveIntegerField(default=1)
        purchase_date = models.DateTimeField(auto_now_add=True)
        is_paid = models.BooleanField(default=False)  # ✅ เพิ่ม field นี้ 

    class PaymentProof(models.Model):
        user = models.ForeignKey(User, on_delete=models.CASCADE)
        equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
        slip = models.ImageField(upload_to='slips/')
        name = models.CharField(max_length=255)
        tel = models.CharField(max_length=20)
        address = models.TextField()
        submitted_at = models.DateTimeField(auto_now_add=True)
        is_verified = models.BooleanField(default=False)