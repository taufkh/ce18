# TH Account Statement - UAT Checklist

## Scope
- Module: `th_account_statement`
- Database: `demo`
- URL: `http://localhost:8069`

## Prerequisites
- At least 2 customer partners with email addresses.
- Invoices and refunds exist in mixed states (`paid`, `in_payment`, `not_paid`, `partial`).
- At least one portal user linked to a customer contact.
- Company logo and address are configured.

## 1. Settings
- Open `Accounting > Configuration > Settings`.
- Verify section `Account Statement` appears.
- Verify save/load for:
  - portal menu toggle
  - mail log toggles
  - filter only unpaid toggle
  - customer and overdue mail template fields
- Expected: values persist after save and refresh.

## 2. Wizard (Generate Statement)
- Open `Account Statement > Generate Statement`.
- Test statement types: customer, customer overdue, vendor, vendor overdue.
- Test period filter options:
  - this month
  - last month
  - this quarter
  - last quarter
  - this year
  - last year
  - custom
- Test payment status filter for customer/vendor.
- Expected:
  - PDF generates without error.
  - XLS downloads without error.
  - Totals equal line sums.
  - Opening balance appears in PDF/XLS.

## 3. Partner Tab (Customer Statement)
- Open a customer partner form.
- Tab `Customer Statement` exists.
- Test `Get Customer Statement` with multiple filters.
- Test actions:
  - Send Filter Customer Statement
  - Print Filter Customer Statement
  - Print Filter Customer Statement XLS
  - Send Customer Statement
  - Print Customer Statement
  - Print Customer Statement XLS
  - Send Overdue Customer Statement
  - Print Overdue Customer Statement
  - Print Overdue Customer Statement XLS
- Expected:
  - tables refresh correctly by filter.
  - totals and ageing values are consistent.

## 4. Action Menu Integration (Partner Form)
- From partner `Action` menu, run send/print actions.
- Expected:
  - actions trigger same behavior as tab buttons.
  - no access error for accounting user.

## 5. Email Behavior (Manual Trigger)
- Trigger send from wizard and partner tab.
- Expected:
  - one email per selected partner.
  - PDF attachment contains only that partner data.
  - template from settings is used when configured.
  - fallback email body used when template not configured.

## 6. Statement Log History
- Open `Account Statement > Statement History`.
- Verify columns:
  - period filter
  - payment status
  - mail subject
  - mail reference
  - mail sent status
- Test filters/group by:
  - statement type
  - mail sent status
  - partner
  - sent by
- Expected: data matches email actions.

## 7. Security
- Login as accounting user A and B.
- Generate/send statements from both users.
- Verify user A cannot see user B logs.
- Login as accounting manager.
- Verify manager can see all logs.

## 8. Portal
- Login as portal user.
- Open `/my/customer_statements`.
- Verify page appears only when portal toggle is enabled.
- Test:
  - date filter and get statement
  - send filtered/normal/overdue statement
  - download PDF/XLS for filtered/normal/overdue
- Expected:
  - only own partner data is shown.
  - downloads are successful and scoped to own partner.

## 9. Regression
- Re-run core accounting flows:
  - create/post invoice
  - register payment
  - create refund
- Verify module does not break standard partner/account views.
