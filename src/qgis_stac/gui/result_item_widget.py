# -*- coding: utf-8 -*-
"""
    Result item widget, used as a template for each search result item.
"""


import datetime
import json
import os
import tempfile

from functools import partial

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapLayer,
    QgsNetworkContentFetcherTask,
    QgsProject,
    QgsRasterLayer,
    QgsTask,
    QgsVectorLayer,
)
from ..lib import planetary_computer as pc

try:
    import urlparse
    from urllib import urlencode
except: # For Python 3
    import urllib.parse as urlparse
    from urllib.parse import urlencode


from ..resources import *
from ..utils import log, tr
from ..definitions.constants import SAS_SUBSCRIPTION_VARIABLE

from ..api.models import (
    ApiCapability,
    AssetLayerType,
    AssetRoles,
    ResourceAsset
)

from ..conf import settings_manager

from .assets_dialog import AssetsDialog
from ..definitions import constants


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/result_item_widget.ui")
)


class ResultItemWidget(QtWidgets.QWidget, WidgetUi):
    """
     Result item widget class, contains logic for displaying the
     item properties, loading and downloading item assets as layers,
     showing the item thumbnail and adding footprint as
     a layer into QGIS.
    """

    footprint_selected = QtCore.pyqtSignal()
    footprint_deselected = QtCore.pyqtSignal()

    def __init__(
        self,
        item,
        main_widget,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.item = item
        self.title_la.setText(item.id)
        self.thumbnail_url = None
        self.date_time_format = "%Y-%m-%dT%H:%M:%S"
        self.simple_date_format = "%m/%d/%Y"
        self.main_widget = main_widget
        self.layer_loader = None
        self.initialize_ui()
        if self.thumbnail_url:
            self.add_thumbnail()

    def initialize_ui(self):
        """ Populate UI inputs when loading the widget"""

        datetime_str = None
        if self.item.properties and \
            self.item.properties.start_date and \
            self.item.proerties.end_date:

            start_date = datetime.datetime.strftime(
                self.item.properties.start_date,
                self.simple_date_format
            )
            end_date = datetime.datetime.strftime(
                self.item.properties.end_date,
                self.simple_date_format
            )

            datetime_str = f"{start_date} - {end_date}"

        elif self.item.properties and \
                self.item.properties.resource_datetime:

            datetime_str = datetime.datetime.strftime(
                self.item.properties.resource_datetime,
                self.simple_date_format
            )

        self.created_date.setText(
            datetime_str
        ) if datetime_str else None

        if self.item.properties.eo_cloud_cover:
            cloud_cover = round(
                self.item.properties.eo_cloud_cover,
                2)

            cloud_cover_integer = int(cloud_cover)

            cloud_cover = cloud_cover_integer \
                if cloud_cover == cloud_cover_integer \
                else cloud_cover

            self.cloud_cover.setText(
                tr(
                    "Cloud cover: {}%"
                   ).format(cloud_cover)
            )

        # Get item collection name if catalogs collections have been stored
        # in the plugin catalog connection settings.
        current_connection = settings_manager.get_current_connection()

        collection = settings_manager.get_collection(
            collection_id=self.item.collection,
            connection=current_connection
        )

        collection_label = collection.title \
            if collection else self.item.collection
        self.collection_name.setText(collection_label)

        thumbnail_url = None
        overview_url = None

        for asset in self.item.assets:
            if AssetRoles.THUMBNAIL.value in asset.roles:
                thumbnail_url = self.sign_asset_href(asset.href)

            elif AssetRoles.OVERVIEW.value in asset.roles:
                overview_url = self.sign_asset_href(asset.href)

        if overview_url:
            params = {
                constants.THUMBNAIL_HEIGHT_PARAM:
                    constants.THUMBNAIL_HEIGHT,
                constants.THUMBNAIL_WIDTH_PARAM:
                    constants.THUMBNAIL_WIDTH,
            }
            overview_url = self.append_url_params(overview_url, params)

        self.thumbnail_url = thumbnail_url \
            if thumbnail_url else overview_url

        self.view_assets_btn.setEnabled(self.item.assets is not None)
        self.view_assets_btn.clicked.connect(self.open_assets_dialog)

        self.footprint_box.setEnabled(self.item.stac_object is not None)
        self.footprint_box.toggled.connect(self.footprint_box_toggled)

    def footprint_box_toggled(self):
        """ Handles logic after the footprint checkbox has been toggled"""
        if self.footprint_box.isChecked():
            self.footprint_selected.emit()
        else:
            self.footprint_deselected.emit()

    def sign_asset_href(self, asset_href):
        """ Signs the SAS based asset href.

        :param asset_href: Asset resource href
        :type asset_href: str

        :returns Signed href or same href if not signing is required
        :rtype str
        """

        # If the plugin defined connection sas subscription key
        # exists use it instead of the environment one.
        sas_key = os.getenv(SAS_SUBSCRIPTION_VARIABLE)
        connection = settings_manager.get_current_connection()

        if connection and \
                connection.capability == ApiCapability.SUPPORT_SAS_TOKEN:
            sas_key = connection.sas_subscription_key \
                if connection.sas_subscription_key else sas_key

            pc.set_subscription_key(sas_key) if sas_key else None

            signed_href = pc.sign(asset_href)
            return signed_href

        return asset_href

    def append_url_params(self, url, params):
        """ Appends the passed params into the url.
        :param url: HTTP URL
        :type url: str

        :param url: URL params
        :type url: dict

        :returns New url updated with params
        :rtype str
        """
        parts = list(urlparse.urlparse(url))

        query = urlparse.parse_qsl(parts[4])
        query += params.items()

        parts[4] = urlencode(query)

        return urlparse.urlunparse(parts)

    def update_inputs(self, enabled):
        """ Updates the inputs widgets state in the main search item widget.
        :param enabled: Whether to enable the inputs or disable them.
        :type enabled: bool
        """
        self.view_assets_btn.setEnabled(enabled)
        self.footprint_box.setEnabled(enabled)

    def open_assets_dialog(self):
        """  Opens the assets dialog for the STAC item.
            Queries the plugin Item from the plugin settings to get the
            most recent updated assets.
        """
        connection = settings_manager.get_current_connection()
        saved_item = settings_manager.get_items(
            connection.id,
            [str(self.item.item_uuid)]
        )
        if saved_item:
            stored_assets = [
                ResourceAsset(
                    href=asset.href,
                    title=asset.title or key,
                    description=asset.description,
                    type=asset.media_type,
                    roles=asset.roles or []
                )
                for key, asset in self.item.stac_object.assets.items()
            ]
            self.item.assets = stored_assets

        assets_dialog = AssetsDialog(
            self.item,
            parent=self,
            main_widget=self.main_widget
        )
        assets_dialog.exec_()

    def add_footprint(self):
        """ Adds the item footprint inside QGIS as a map layer"""
        layer_file = tempfile.NamedTemporaryFile(
            mode="w+",
            suffix='.geojson',
            delete=False
        )
        layer_name = f"{self.item.id}_footprint"
        json.dump(self.item.stac_object.to_dict(), layer_file)

        layer_file.flush()

        layer = QgsVectorLayer(
            layer_file.name,
            layer_name,
            AssetLayerType.VECTOR.value
        )
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.main_widget.show_message(
                tr("Successfully loaded footprint layer."),
                level=Qgis.Info
            )

        else:
            self.main_widget.show_message(
                tr(
                    "Couldn't load footprint into QGIS,"
                    " its layer is not valid."
                ),
                level=Qgis.Critical
            )

    def add_thumbnail(self):
        """ Downloads and loads the STAC Item thumbnail"""
        request = QtNetwork.QNetworkRequest(
            QtCore.QUrl(
                self.thumbnail_url
            )
        )
        self.network_task(
            request,
            self.thumbnail_response
        )

    def thumbnail_response(self, content):
        """ Callback to handle the thumbnail network response.
            Sets the thumbnail image data into the widget thumbnail label.

        :param content: Network response data
        :type content: QByteArray
        """
        thumbnail_image = QtGui.QImage.fromData(content)

        if thumbnail_image:
            thumbnail_pixmap = QtGui.QPixmap.fromImage(thumbnail_image)
            self.thumbnail_la.setPixmap(thumbnail_pixmap)

    def network_task(
            self,
            request,
            handler,
            auth_config=""
    ):
        """Fetches the response from the given request.

        :param request: Network request
        :type request: QNetworkRequest

        :param handler: Callback function to handle the response
        :type handler: Callable

        :param auth_config: Authentication configuration string
        :type auth_config: str
        """
        task = QgsNetworkContentFetcherTask(
            request,
            authcfg=auth_config
        )
        response_handler = partial(
            self.response,
            task,
            handler
        )
        task.fetched.connect(response_handler)
        task.run()

    def response(
            self,
            task,
            handler
    ):
        """Handle the return response

        :param task: QGIS task that fetches network content
        :type task:  QgsNetworkContentFetcherTask
        """
        reply = task.reply()
        error = reply.error()
        if error == QtNetwork.QNetworkReply.NoError:
            contents: QtCore.QByteArray = reply.readAll()
            handler(contents)
        else:
            log(tr("Problem fetching response from network"))


def add_footprint_helper(item, main_widget):
    """ Adds the item footprint inside QGIS as a map layer

    :param item: STAC item whose footprint is going to be added
    :type item: Item

    :param main_widget: Parent widget that the function is called from
    :type main_widget: QWidget
    """
    layer_file = tempfile.NamedTemporaryFile(
        mode="w+",
        suffix='.geojson',
        delete=False
    )
    layer_name = f"{item.id}_footprint"
    json.dump(item.stac_object.to_dict(), layer_file)

    layer_file.flush()

    layer = QgsVectorLayer(
        layer_file.name,
        layer_name,
        AssetLayerType.VECTOR.value
    )
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        main_widget.show_message(
            tr(
                "Successfully loaded footprint layer for item {}."
            ).format(
                item.id
            ),
            level=Qgis.Info
        )

    else:
        main_widget.show_message(
            tr(
                "Couldn't load footprint into QGIS for item {},"
                " its layer is not valid."
            ).format(item.id),
            level=Qgis.Critical
        )
