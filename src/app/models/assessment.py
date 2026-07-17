from django.db import models


class PoemAssessment(models.Model):
    poem = models.OneToOneField(
        "app.Poem",
        on_delete=models.CASCADE,
        related_name="assessment",
    )

    freshness = models.SmallIntegerField(null=True, blank=True)
    emotional_density = models.SmallIntegerField(null=True, blank=True)
    voice = models.SmallIntegerField(null=True, blank=True)
    completeness = models.SmallIntegerField(null=True, blank=True)
    anti_repeat = models.SmallIntegerField(null=True, blank=True)

    comment = models.TextField(blank=True, default="")
    model_name = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app_poem_assessment"

    def __str__(self) -> str:
        return f"Assessment for poem {self.poem_id}"
