from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestStatementLogSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("account.group_account_user")
        cls.user_a = cls.env["res.users"].create(
            {
                "name": "Statement User A",
                "login": "statement_user_a",
                "email": "a@example.com",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "Statement User B",
                "login": "statement_user_b",
                "email": "b@example.com",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Security Partner"})

        cls.log_a = cls.env["account.statement.log"].sudo().create(
            {
                "partner_id": cls.partner.id,
                "statement_type": "customer",
                "sent_by": cls.user_a.id,
                "state": "sent",
            }
        )
        cls.log_b = cls.env["account.statement.log"].sudo().create(
            {
                "partner_id": cls.partner.id,
                "statement_type": "customer",
                "sent_by": cls.user_b.id,
                "state": "sent",
            }
        )

    def test_account_user_sees_only_own_logs(self):
        logs_user_a = self.env["account.statement.log"].with_user(self.user_a).search([])
        self.assertIn(self.log_a, logs_user_a)
        self.assertNotIn(self.log_b, logs_user_a)
