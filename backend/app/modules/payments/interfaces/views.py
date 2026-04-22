import json

from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.http import HttpResponseNotFound
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app.modules.payments.application.alert_signal_queries import payment_alert_signal_queries
from app.modules.payments.application.hosted_redirect_commands import hosted_redirect_commands
from app.modules.payments.application.hosted_return_commands import hosted_return_commands
from app.modules.payments.application.webhook_commands import payment_webhook_commands


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        raw_body = request.body or b""
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonResponse({"result": "payment-webhook-invalid-json"}, status=400)

        if not isinstance(payload, dict):
            return JsonResponse({"result": "payment-webhook-invalid-json"}, status=400)

        provided_token = str(request.headers.get("X-Hubx-Webhook-Token", "") or "").strip()
        signature_header = str(getattr(settings, "PAGARME_WEBHOOK_SIGNATURE_HEADER", "X-Hub-Signature") or "").strip()
        provided_signature = str(request.headers.get(signature_header, "") or "").strip()
        result, status_code = payment_webhook_commands.process_webhook(
            payload=payload,
            provided_token=provided_token,
            raw_body=raw_body,
            provided_signature=provided_signature,
        )
        return JsonResponse({"result": result}, status=status_code)


class HostedPaymentRedirectView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        back_url = str(request.GET.get("back_url", "") or "").strip()
        safe_back_url = back_url if back_url.startswith("/") else ""
        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        result, action_url = hosted_redirect_commands.resolve_redirect_url(
            tenant_id=tenant_id,
            attempt_key=str(kwargs.get("attempt_key") or ""),
        )
        if result == "hosted-payment-ready" and action_url:
            return HttpResponseRedirect(action_url)
        if safe_back_url:
            separator = "&" if "?" in safe_back_url else "?"
            return HttpResponseRedirect(f"{safe_back_url}{separator}result=hosted-payment-unavailable")
        return HttpResponseNotFound("Pagamento hospedado indisponível.")


class HostedPaymentReturnView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        back_url = str(request.GET.get("back_url", "") or "").strip()
        safe_back_url = back_url if back_url.startswith("/") else ""
        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        result = hosted_return_commands.register_return(
            tenant_id=tenant_id,
            attempt_key=str(kwargs.get("attempt_key") or ""),
            status_hint=str(request.GET.get("status") or request.GET.get("result") or request.GET.get("outcome") or ""),
            payment_reference=str(request.GET.get("payment_reference") or request.GET.get("reference") or ""),
            provider_label=str(request.GET.get("provider") or request.GET.get("payment_source_label") or ""),
        )
        if safe_back_url:
            separator = "&" if "?" in safe_back_url else "?"
            return HttpResponseRedirect(f"{safe_back_url}{separator}result={result}")
        if result == "hosted-payment-unavailable":
            return HttpResponseNotFound("Retorno de pagamento indisponível.")
        return JsonResponse({"result": result}, status=200)


class PaymentAlertMetricsView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        configured_token = str(getattr(settings, "PAYMENTS_OBSERVABILITY_TOKEN", "") or "").strip()
        if not configured_token:
            return HttpResponseNotFound("Métricas de pagamento indisponíveis.")

        provided_token = str(request.headers.get("X-Hubx-Observability-Token", "") or "").strip()
        if not provided_token:
            authorization_header = str(request.headers.get("Authorization", "") or "").strip()
            if authorization_header.lower().startswith("bearer "):
                provided_token = authorization_header[7:].strip()
        if provided_token != configured_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

        payload = payment_alert_signal_queries.export_prometheus_metrics()
        return HttpResponse(
            payload,
            status=200,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )
