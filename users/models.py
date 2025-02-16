from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator
import os
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.conf import settings
import boto3
from django.core.exceptions import ValidationError


def delete_s3_file(file_path):
    """Helper function to delete a file from S3"""
    if not file_path:
        return

    try:
        # Get the relative path from the FileField
        key = str(file_path)

        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        # Delete the file
        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )
        print(f"Successfully deleted file: {key} from bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
    except Exception as e:
        print(f"Error deleting file from S3: {str(e)}")


def validate_image_extension(value):
    """Validator for jpg/jpeg file extensions"""
    import os
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg']
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension. Please upload a JPG or JPEG file.')


class FileMetadata(models.Model):
    """
    Model to store metadata for uploaded files
    """
    file_title = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(1), MaxLengthValidator(255)]
    )
    upload_timestamp = models.DateTimeField(default=timezone.now)
    description = models.TextField()
    keywords = models.CharField(max_length=500, help_text="Comma-separated keywords")

    # Generic foreign key to associate with any file field
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.file_title

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]


class TravelPlan(models.Model):
    """Model for a travel plan"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    users = models.ManyToManyField(User, related_name='plans')
    plan_name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(1), MaxLengthValidator(100)]
    )
    group_size = models.IntegerField()
    trip_description = models.TextField()
    jpg_upload_file = models.FileField(upload_to='uploads/main_plan_jpgs/', blank=True, null=True, validators=[validate_image_extension])
    txt_upload_file = models.FileField(upload_to='uploads/txts/', blank=True, null=True)
    pdf_upload_file = models.FileField(upload_to='uploads/pdfs/', blank=True, null=True)
    primary_group_code = models.CharField(max_length=100)

    jpg_metadata = models.OneToOneField(
        FileMetadata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jpg_travel_plan"
    )
    txt_metadata = models.OneToOneField(
        FileMetadata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="txt_travel_plan"
    )
    pdf_metadata = models.OneToOneField(
        FileMetadata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pdf_travel_plan"
    )
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def delete(self, *args, **kwargs):
        # Delete files from S3 before deleting the model instance
        if self.jpg_upload_file:
            delete_s3_file(self.jpg_upload_file.name)
        if self.txt_upload_file:
            delete_s3_file(self.txt_upload_file.name)
        if self.pdf_upload_file:
            delete_s3_file(self.pdf_upload_file.name)

        # Delete the model instance
        super().delete(*args, **kwargs)


class Destination(models.Model):
    """Model for a destination"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    users = models.ManyToManyField(User, related_name='destinations')
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE, related_name='destinations')
    destination_name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(1), MaxLengthValidator(100)]
    )
    destination_description = models.TextField()
    jpg_upload_file = models.FileField(upload_to='uploads/destinations_jpgs/', blank=True, null=True, validators=[validate_image_extension])
    txt_upload_file = models.FileField(upload_to='uploads/destinations_txts/', blank=True, null=True)
    pdf_upload_file = models.FileField(upload_to='uploads/destination_pdfs/', blank=True, null=True)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    location_address = models.TextField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    jpg_metadata = models.OneToOneField(
        FileMetadata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jpg_destination"
    )
    txt_metadata = models.OneToOneField(
        FileMetadata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="txt_destination"
    )
    pdf_metadata = models.OneToOneField(
        FileMetadata,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pdf_destination"
    )

    # def __str__(self):
    #     return self.plan_name

    def delete(self, *args, **kwargs):
        # Delete files from S3 before deleting the model instance
        if self.jpg_upload_file:
            delete_s3_file(self.jpg_upload_file.name)
        if self.txt_upload_file:
            delete_s3_file(self.txt_upload_file.name)
        if self.pdf_upload_file:
            delete_s3_file(self.pdf_upload_file.name)

        # Delete the model instance
        super().delete(*args, **kwargs)


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='comments')
    commentText = models.TextField()
    upload_timestamp = models.DateTimeField(default=timezone.now)


class Invite(models.Model):
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE, related_name='invites')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    requested_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invites')

    class Meta:
        unique_together = ('travel_plan', 'requested_by', 'requested_to')
        indexes = [
            models.Index(fields=['travel_plan', 'requested_by', 'requested_to']),
        ]


class Expense(models.Model):
    """Model for tracking expenses for a destination"""
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='expenses')
    expense_name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(1), MaxLengthValidator(100)]
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    expense_date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['destination', 'expense_date']),
        ]

    def __str__(self):
        return f"{self.expense_name} - ${self.amount}"
