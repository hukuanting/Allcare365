from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from .models import Patient, PatientPractitionerLink, Practitioner


class PatientAdminAuthorizationTests(TestCase):
    def setUp(self):
        self.linked_patient = Patient.objects.create(first_name="Linked", last_name="Patient")
        self.unrelated_patient = Patient.objects.create(first_name="Private", last_name="Patient")
        self.view_permission = Permission.objects.get(
            content_type__app_label="patients", codename="view_patient"
        )
        self.change_permission = Permission.objects.get(
            content_type__app_label="patients", codename="change_patient"
        )

    def _staff(self, username):
        user = User.objects.create_user(username=username, password="password", is_staff=True)
        user.user_permissions.add(self.view_permission, self.change_permission)
        return user

    def test_model_view_permission_does_not_disclose_unrelated_patient(self):
        user = self._staff("admin-view-only")
        self.client.force_login(user)

        response = self.client.get(reverse("admin:patients_patient_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.linked_patient.first_name)
        self.assertNotContains(response, self.unrelated_patient.first_name)
        response = self.client.get(
            reverse("admin:patients_patient_change", args=[self.unrelated_patient.pk])
        )
        # Django admin redirects a hidden object lookup back to the changelist
        # rather than rendering a 404.  The scoped changelist above is the
        # disclosure boundary; this response contains no object form.
        self.assertEqual(response.status_code, 302)

    def test_read_only_care_link_cannot_change_admin_record(self):
        user = self._staff("admin-linked-read")
        practitioner = Practitioner.objects.create(
            user=user, first_name="Admin", last_name="Reader"
        )
        PatientPractitionerLink.objects.create(
            patient=self.linked_patient,
            practitioner=practitioner,
            permissions_json={"patient_data": "read"},
        )
        self.client.force_login(user)
        change_url = reverse("admin:patients_patient_change", args=[self.linked_patient.pk])

        self.assertEqual(self.client.get(change_url).status_code, 200)
        response = self.client.post(
            change_url,
            {"first_name": "Changed", "last_name": "Patient", "status": "active"},
        )

        self.assertEqual(response.status_code, 403)
        self.linked_patient.refresh_from_db()
        self.assertEqual(self.linked_patient.first_name, "Linked")

    def test_explicit_global_permissions_allow_authorized_staff(self):
        user = self._staff("admin-global")
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="patients", codename="access_all_clinical_records"
            ),
            Permission.objects.get(
                content_type__app_label="patients", codename="edit_all_clinical_records"
            ),
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:patients_patient_changelist"))
        self.assertContains(response, self.linked_patient.first_name)
        self.assertContains(response, self.unrelated_patient.first_name)
        response = self.client.post(
            reverse("admin:patients_patient_change", args=[self.unrelated_patient.pk]),
            {
                "first_name": "Updated",
                "last_name": "Patient",
                "status": "active",
                "country": "Taiwan",
                "preferred_language": "zh-tw",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.unrelated_patient.refresh_from_db()
        self.assertEqual(self.unrelated_patient.first_name, "Updated")
