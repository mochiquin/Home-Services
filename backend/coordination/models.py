from django.db import models
from django.db.models import F, Q
from projects.models import Project
# from tnm_integration.models import TnmJob  # Removed - TNM jobs no longer supported
from contributors.models import Contributor, CodeFile

class CoordinationRun(models.Model):
    """A single execution of coordination metrics calculation.

    Stores parameters (algorithm, sources, configs) and summary stats
    produced by the run for later inspection and downstream processing.
    """

    class Algo(models.TextChoices):
        STC = "STC", "STC"
        MC_STC = "MC-STC", "MC-STC"

    class TdSource(models.TextChoices):
        LD = "LD", "Logical (co-change)"
        SD = "SD", "Syntactic"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="coord_runs")
    # job field removed - TNM jobs no longer supported
    algorithm = models.CharField(max_length=16, choices=Algo.choices)
    td_source = models.CharField(max_length=8, choices=TdSource.choices)
    ca_source = models.CharField(max_length=32)  # user_changed_files / co_edit / ...
    class_config = models.JSONField(default=dict, blank=True)  # MC-STC thresholds/keywords
    time_window = models.CharField(max_length=64, blank=True, null=True)
    score = models.DecimalField(max_digits=6, decimal_places=3)
    cr_count = models.IntegerField()
    diff_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "created_at"], name="idx_run_proj_time"),
            models.Index(fields=["algorithm", "created_at"], name="idx_run_algo_time"),
        ]

    def __str__(self) -> str:
        return f"CoordinationRun(project_id={self.project_id}, algo={self.algorithm})"

class TaEntry(models.Model):
    """Task assignment (TA) entry: contributor ↔ file edit counts."""
    # job field removed - TNM jobs no longer supported
    contributor = models.ForeignKey(Contributor, on_delete=models.PROTECT)
    file = models.ForeignKey(CodeFile, on_delete=models.PROTECT)
    edit_count = models.IntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["contributor", "file"], name="uq_ta")]
        indexes = [models.Index(fields=["edit_count"], name="idx_ta_edit")]

    def __str__(self) -> str:
        return f"TA(contrib_id={self.contributor_id}, file_id={self.file_id})"

class TdEdge(models.Model):
    """Technical dependency (TD) edge between files, weighted by co-change."""
    # job field removed - TNM jobs no longer supported
    file_a = models.ForeignKey(CodeFile, on_delete=models.PROTECT, related_name="+")
    file_b = models.ForeignKey(CodeFile, on_delete=models.PROTECT, related_name="+")
    weight = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["file_a", "file_b"], name="uq_td"),
            models.CheckConstraint(check=Q(file_a__lt=F("file_b")), name="ck_td_order"),
        ]
        indexes = [models.Index(fields=["weight"], name="idx_td_weight")]

    def __str__(self) -> str:
        return f"TD(files=({self.file_a_id},{self.file_b_id}), w={self.weight})"

class CaEdge(models.Model):
    """Coordination activity (CA) edge between contributors with evidence type."""
    class Evidence(models.TextChoices):
        SAME_COMMIT = "same_commit", "Same commit"
        SAME_FILE = "same_file", "Same file"
        CO_EDIT = "co_edit", "Co-edit"

    # job field removed - TNM jobs no longer supported
    contributor_i = models.ForeignKey(Contributor, on_delete=models.PROTECT, related_name="+")
    contributor_j = models.ForeignKey(Contributor, on_delete=models.PROTECT, related_name="+")
    weight = models.IntegerField()
    evidence = models.CharField(max_length=24, choices=Evidence.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["contributor_i", "contributor_j"], name="uq_ca"),
            models.CheckConstraint(check=Q(contributor_i__lt=F("contributor_j")), name="ck_ca_order"),
        ]
        indexes = [models.Index(fields=["weight"], name="idx_ca_weight")]

    def __str__(self) -> str:
        return f"CA(u=({self.contributor_i_id},{self.contributor_j_id}), w={self.weight})"

class CrEdge(models.Model):  # Optional: materialized Coordination Requirement edges for explanation/visualization
    run = models.ForeignKey(CoordinationRun, on_delete=models.CASCADE, related_name="cr_edges")
    contributor_i = models.ForeignKey(Contributor, on_delete=models.PROTECT, related_name="+")
    contributor_j = models.ForeignKey(Contributor, on_delete=models.PROTECT, related_name="+")
    weight = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "contributor_i", "contributor_j"], name="uq_cr"),
            models.CheckConstraint(check=Q(contributor_i__lt=F("contributor_j")), name="ck_cr_order"),
        ]
        indexes = [models.Index(fields=["run", "weight"], name="idx_cr_run_weight")]

    def __str__(self) -> str:
        return f"CR(run_id={self.run_id}, u=({self.contributor_i_id},{self.contributor_j_id}), w={self.weight})"

class FunctionalClass(models.Model):
    """Functional role/class for contributors, e.g., DEV/SEC/OPS."""
    code = models.CharField(max_length=32, unique=True)  # DEV / SEC / OPS ...
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)

class ContributorClassification(models.Model):
    """Classification assignment of a contributor within a project."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="contrib_classes")
    contributor = models.ForeignKey(Contributor, on_delete=models.CASCADE, related_name="classifications")
    class_ref = models.ForeignKey(FunctionalClass, on_delete=models.PROTECT, related_name="members")
    # basis_job field removed - TNM jobs no longer supported
    method = models.CharField(max_length=40)  # keyword_ratio/manual/model
    threshold = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    evidence = models.JSONField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "contributor"], name="uq_contrib_class"),
        ]
        indexes = [models.Index(fields=["class_ref", "project"], name="idx_class_lookup")]

    def __str__(self) -> str:
        return f"Class(project_id={self.project_id}, contrib_id={self.contributor_id}, class_id={self.class_ref_id})"
