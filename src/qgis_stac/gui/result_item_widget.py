import os

from functools import partial

from qgis.PyQt import (
    QtGui,
    QtCore,
    QtWidgets,
    QtNetwork
)

from qgis.PyQt.uic import loadUiType

from  qgis.core import (
    QgsApplication,
    QgsNetworkContentFetcherTask,
    QgsTask
)

from ..resources import *
from ..utils import log


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/result_item_widget.ui")
)


class ResultItemWidget(QtWidgets.QWidget, WidgetUi):

    def __init__(
        self,
        item,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.item = item
        self.title_la.setText(item.id)
        self.collection_name.setText(item.collection)
        self.thumbnail_url = None
        self.initialize_ui()
        # if self.thumbnail_url:
        #     self.add_thumbnail()

    def initialize_ui(self):

        self.created_date.setText(
            str(self.item.properties.resource_datetime)
        )
        layer_types = [
            "image/tiff; "
            "application=geotiff; "
            "profile=cloud-optimized"
        ]

        for asset in self.item.assets:
            self.assets_download_box.addItem(
                asset.title,
                asset.href
            )
            if asset.type in layer_types:
                self.assets_load_box.addItem(
                    asset.title,
                    asset.href
                )
            if 'thumbnail' in asset.roles:
                self.thumbnail_url = asset.href

    def add_thumbnail(self):
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
        """Fetches the response from the given request"""
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
            task: QgsNetworkContentFetcherTask,
            handler
    ):
        """Handle the return response """
        reply = task.reply()
        error = reply.error()
        if error == QtNetwork.QNetworkReply.NoError:
            contents: QtCore.QByteArray = reply.readAll()
            handler(contents)
        else:
            log("Problem fetching response from network")


class ThumbnailLoader(QgsTask):
    def __init__(
        self,
        thumbnail_reply: QtCore.QByteArray,
        label: QtWidgets.QLabel
    ):

        super().__init__()
        self.content = thumbnail_reply
        self.label = label
        self.thumbnail_image = None

    def run(self):
        self.thumbnail_image = QtGui.QImage.fromData(self.content)
        return True

    def finished(self, result: bool):
        if result:
            thumbnail_pixmap = QtGui.QPixmap.fromImage(self.thumbnail_image)
            self.label.setPixmap(thumbnail_pixmap)
        else:
            log(f"Couldn't load thumbnail")
