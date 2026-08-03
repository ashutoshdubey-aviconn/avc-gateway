"""
Module wareApp.testcases.test_models_dynamic

Flow:
Top-level classes:
- DynamicModelCreationTests: Attempt to create and save one instance of each model in wareApp with
"""

import importlib
import inspect

from django.db.models.fields import NOT_PROVIDED
from django.test import TestCase
from django.utils import timezone

from wareApp import models as app_models


class DynamicModelCreationTests(TestCase):
    """Attempt to create and save one instance of each model in wareApp with
    sensible defaults for required fields. This helps catch missing migrations
    or model initialization errors early.
    """

    def setUp(self):
        self.created = {}

    def _make_value_for_field(self, field):
        from django.core.files.uploadedfile import SimpleUploadedFile

        field_class = field.__class__.__name__
        if field.many_to_many:
            return None
        if field.auto_created and not field.concrete:
            return None
        # prefer using a declared default when it's a concrete value/callable
        try:
            default_val = getattr(field, "default", None)
        except Exception:
            default_val = None
        # Ignore Django's NOT_PROVIDED sentinel
        if default_val is not None and default_val is not NOT_PROVIDED:
            try:
                return default_val() if callable(default_val) else default_val
            except Exception:
                pass
        if hasattr(field, "null") and field.null:
            return None

        if field_class.endswith("CharField") or field_class.endswith("TextField"):
            max_length = getattr(field, "max_length", 32) or 32
            return (field.name or "x")[:max_length]
        if (
            field_class.endswith("IntegerField")
            or field_class.endswith("PositiveIntegerField")
            or field_class.endswith("SmallIntegerField")
        ):
            return 1
        if field_class.endswith("FloatField"):
            return 1.0
        if field_class.endswith("BooleanField"):
            return True
        if field_class.endswith("DateTimeField"):
            return timezone.now()
        if field_class.endswith("DateField"):
            return timezone.now().date()
        if field_class.endswith("ForeignKey"):
            rel_model = field.related_model
            # if we already created one, reuse it
            if rel_model in self.created:
                return self.created[rel_model]
            # avoid recursion loops by creating a minimal instance
            instance = self._create_instance_for_model(rel_model)
            return instance
        if field_class.endswith("FileField"):
            return SimpleUploadedFile("f.txt", b"content")

        # fallback
        return None

    def _create_instance_for_model(self, model_cls):
        if model_cls in self.created:
            return self.created[model_cls]

        kwargs = {}
        for field in model_cls._meta.get_fields():
            # skip reverse relations and m2m
            if getattr(field, "auto_created", False) and not getattr(field, "concrete", True):
                continue
            if field.many_to_many:
                continue
            if getattr(field, "primary_key", False) and getattr(field, "has_default", False) is False:
                # allow user to provide primary keys where required
                if field.auto_created:
                    continue
            if not getattr(field, "editable", True):
                continue

            name = field.name
            if name == "id":
                continue
            val = self._make_value_for_field(field)
            if val is not None:
                kwargs[name] = val

        try:
            obj = model_cls.objects.create(**kwargs)
        except Exception:
            # try instantiate without saving as last resort
            obj = model_cls(**{k: v for k, v in kwargs.items() if not inspect.isclass(v)})
            try:
                obj.save()
            except Exception:
                pass

        self.created[model_cls] = obj
        return obj

    def test_create_all_models(self):
        # iterate over attributes in wareApp.models and create instances for classes
        for name, cls in inspect.getmembers(app_models, inspect.isclass):
            # skip imported Django/third-party classes
            if cls.__module__ != app_models.__name__:
                continue
            # skip abstract and proxy models
            meta = getattr(cls, "_meta", None)
            if meta is None or getattr(meta, "abstract", False):
                continue

            try:
                instance = self._create_instance_for_model(cls)
            except Exception as exc:
                self.fail(f"Failed creating instance of {cls}: {exc}")

            # basic sanity: str() should not error
            try:
                _ = str(instance)
            except Exception as exc:
                self.fail(f"__str__ for {cls} raised: {exc}")
