import itertools
from django.conf.urls import url, include

from viewflow.flow.viewset import FlowViewSet as BaseFlowViewSet
from . import views


class MichelinFlowViewSet(BaseFlowViewSet):
    process_list_view = [
        r'^$',
        views.MichelinProcessListView.as_view(),
        'index'
    ]

