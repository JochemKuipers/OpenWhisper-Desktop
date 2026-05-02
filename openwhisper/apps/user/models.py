from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    phone_number: models.CharField = models.CharField(max_length=10, null=True, blank=True)
    last_login = models.DateTimeField(auto_now=True)

    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio: models.TextField = models.TextField(max_length=500, null=True, blank=True)
    birth_date: models.DateField = models.DateField(null=True, blank=True)
    gender: models.CharField = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        null=True,
        blank=True,
    )
    location: models.CharField = models.CharField(max_length=100, null=True, blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
    
    friends: models.ManyToManyField = models.ManyToManyField("self", blank=True)

    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        unique_together = ["username", "email", "phone_number"]
        db_table = "users"
        app_label = "user"


class FriendRequest(models.Model):
    """Pending invitation before symmetric friendship is established."""

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friend_requests_sent",
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="friend_requests_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_friend_requests"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="unique_friend_request_direction",
            ),
        ]
        indexes = [
            models.Index(fields=["to_user", "-created_at"]),
            models.Index(fields=["from_user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.from_user_id} → {self.to_user_id}"
