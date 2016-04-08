from priorityqueue import HandlerClassSelector, displayDelegateSelector, initialHashHandler
from widgets import EditWidget
from config import conf
from pane import Pane


class SingletonHandler( Pane ):
	def __init__(self, modulName, modulInfo, *args, **kwargs):
		icon = "icons/modules/singleton.svg"
		if "icon" in modulInfo.keys():
			icon = modulInfo["icon"]

		super( SingletonHandler, self ).__init__(modulInfo["visibleName"], icon)
		self.modulName = modulName
		self.modulInfo = modulInfo
		if "hideInMainBar" in modulInfo.keys() and modulInfo["hideInMainBar"]:
			self["style"]["display"] = "none"
		initialHashHandler.insert( 1, self.canHandleInitialHash, self.handleInitialHash)

	def canHandleInitialHash(self, pathList, params ):
		if len(pathList)>1:
			if pathList[0]==self.modulName and pathList[1]=="edit":
				return( True )
		return( False )

	def handleInitialHash(self, pathList, params):
		assert self.canHandleInitialHash( pathList, params )
		edwg = EditWidget( self.modulName, EditWidget.appSingleton, hashArgs=(params or None))
		self.addWidget( edwg )
		self.focus()

	@staticmethod
	def canHandle( modulName, modulInfo ):
		return( modulInfo["handler"]=="singleton" or modulInfo["handler"].startswith("singleton."))

	def onClick(self, *args, **kwargs ):
		if not len(self.widgetsDomElm._children):
			self.addWidget( EditWidget( modul=self.modulName, applicationType=EditWidget.appSingleton ) )
		super( SingletonHandler, self ).onClick( *args, **kwargs )


HandlerClassSelector.insert( 3, SingletonHandler.canHandle, SingletonHandler )
