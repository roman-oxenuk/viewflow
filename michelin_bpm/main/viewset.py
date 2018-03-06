# -*- coding: utf-8 -*-
from viewflow.flow.viewset import FlowViewSet as BaseFlowViewSet
from . import views


class MichelinFlowViewSet(BaseFlowViewSet):

    process_list_view = [
        r'^$',
        views.MichelinProcessListView.as_view(),
        'index'
    ]

    detail_proposal_view = [
        r'^(?P<process_pk>\d+)/show/$',
        views.ShowProposalView.as_view(),
        'show_proposal'
    ]
