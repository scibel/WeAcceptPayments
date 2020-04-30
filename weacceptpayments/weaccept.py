"""
Payments for WeAccept.co
"""
from .exceptions import AuthError, OrderError, PaymentError, ItemFormatError
from .misc import HTTP_CODES
from .consts import URLS
from .mixins import NetworkingClassMixin, BaseSignatureMixin


class WeAcceptAuth(BaseSignatureMixin, NetworkingClassMixin):
    exception_class = AuthError

    _allowed_kwargs = [
        'api_key'
    ]

    _MANDATORY_KWARGS = [
        'api_key'
    ]

    def start(self):
        """
        no need to validate api_key, mandatory kwargs are validated by the BaseSignatureMixin.
        """

        self.post_request_kwargs(URLS.AUTH_URL)

        if self.request.status_code == HTTP_CODES.CREATED:
            self.auth_token = self.response['token']
            setattr(self, 'merchant_id', self.response['profile']['id'])
        else:
            raise self.exception_class(self.response)


class WeAcceptOrder(BaseSignatureMixin, NetworkingClassMixin):
    exception_class = OrderError

    _allowed_kwargs = [
        'delivery_needed', 'merchant_id', 'amount_cents', 'currency', 'merchant_order_id',
        'items', 'shipping_data', 'auth', 'auth_token', 'merchant_id'
    ]

    _MANDATORY_KWARGS = [
        # amount cents must be specified and the server says duplicate order if it's not.
        'merchant_order_id', 'merchant_id', 'amount_cents'
    ]

    _MANDATORY_ITEM_DATA = [
        'name', 'amount_cents'
    ]  # @TODO

    def __init__(self, **kwargs):
        auth = kwargs.pop('auth', None)

        if not auth:
            if 'auth_token' not in kwargs:
                raise self.exception_class('Missing auth_token in keyword arguments')
            if 'merchant_id' not in kwargs:
                raise self.exception_class('Missing merchant_id in keyword arguments')
        else:
            kwargs['auth_token'] = auth.auth_token
            kwargs['merchant_id'] = auth.merchant_id

        # if 'delivery_needed' in kwargs and kwargs['delivery_needed'] == True:

        kwargs.setdefault('currency', 'EGP')
        kwargs.setdefault('delivery_needed', False)

        if kwargs['delivery_needed']:
            if 'shipping_data' not in kwargs:
                raise self.exception_class('Delivery needed but no shipping_data specified.')

        self.kwargs = kwargs
        super().__init__(**kwargs)

    def _validate_items(self):
        """
        Should make sure that each item in items has a name & a price.
        Otherwise, We get a server error. This is important as the server
        doesn't respond well to this.

        Duo to the way their JSON API is implemented, We can create an empty order and thus
        This method only validates items if they are provided, Otherwise it returns nothing.

        """
        items = self.kwargs.get('items', None)

        if not items:
            return

        if len(items) == 0:
            raise ItemFormatError('Empty items list.')

        for item in items:
            if len(item.keys()) == len(self.get_mandatory_item_data()):
                for key in self.get_mandatory_item_data():
                    if key not in item:
                        raise ItemFormatError(f'Missing {key} from {item}')
            else:
                raise ItemFormatError('Items should only have name and amount_cents')

    def get_mandatory_item_data(self):
        """
        'name', 'amount_cents' are mandatory. Server error if they are not included.

        Must return a list.
        """
        return self._MANDATORY_ITEM_DATA

    def start(self):

        self._validate_items()

        self.post_request_kwargs(URLS.ORDERS_URL)

        if self.request.status_code == HTTP_CODES.CREATED:
            setattr(self, 'order_id', self.response['id'])
        else:
            raise self.exception_class(self.response)


class WeAcceptPayment(BaseSignatureMixin, NetworkingClassMixin):
    """
    Create a payment for WeAccept.co

    """
    exception_class = PaymentError

    _allowed_kwargs = [
        'amount_cents', 'expiration', 'billing_data', 'currency', 'integration_id',
        'lock_order_when_paid', 'auth', 'auth_token', 'order', 'order_id'
    ]

    _MANDATORY_KWARGS = [
        'integration_id', 'billing_data', 'amount_cents'
    ]

    def __init__(self, **kwargs):
        auth = kwargs.pop('auth', None)
        order = kwargs.pop('order', None)

        if not auth:
            if 'auth_token' not in kwargs:
                raise self.exception_class('Missing auth_token in keyword arguments')
        else:
            kwargs['auth_token'] = auth.auth_token

        if not order:
            if 'order_id' not in kwargs:
                raise self.exception_class('Missing order_id in keyword arguments')
        else:
            kwargs['order_id'] = order.order_id

        kwargs.setdefault('currency', 'EGP')
        kwargs.setdefault('lock_order_when_paid', False)

        self.kwargs = kwargs
        super().__init__(**kwargs)

    def start(self):

        self._validate_payment_data()

        self.post_request_kwargs(URLS.PAYMENT_KEY_URL)

        if 'token' in self.response:
            setattr(self, 'token', self.response['token'])
        else:
            raise self.exception_class(self.response)

    def _validate_payment_data(self):
        """
        Loop through all the mandatory data needed by the server to see if they are provided in the kwargs.
        If they are not, Raise a PaymentError.
        """
        for item in self._MANDATORY_KWARGS:
            if item not in self.kwargs:
                raise self.exception_class(f'Missing {item} in payment_data')
