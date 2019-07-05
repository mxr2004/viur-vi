# -*- coding: utf-8 -*-
import html5
from config import conf
from i18n import translate
from network import NetworkService
from pane import Pane
from priorityqueue import actionDelegateSelector
from widgets.button import Button
from widgets.edit import EditWidget


class AddNodeAction(Button):
	"""
		Adds a new directory to a tree.simple application.
	"""
	def __init__(self, *args, **kwargs):
		super( AddNodeAction, self ).__init__( translate("Add Node"), icon="icons-add-folder", *args, **kwargs )
		self["class"] = "bar-item btn btn--small btn--mkdir btn--primary"

	@staticmethod
	def isSuitableFor( module, handler, actionName ):
		if module is None or module not in conf["modules"].keys():
			return False

		correctAction = actionName=="add.node"
		correctHandler = handler == "tree.simple" or handler.startswith("tree.simple.")
		hasAccess = conf["currentUser"] and ("root" in conf["currentUser"]["access"] or module+"-add" in conf["currentUser"]["access"])
		isDisabled = module is not None and "disabledFunctions" in conf["modules"][module].keys() and conf["modules"][module]["disabledFunctions"] and "add-node" in conf["modules"][module]["disabledFunctions"]

		return correctAction and correctHandler and hasAccess and not isDisabled


	def onClick(self, sender=None):
		i = html5.ext.InputDialog(
			translate("Directory Name"),
			successHandler=self.createDir,
			title=translate("Create directory"),
			successLbl=translate("Create")
		)

		i.addClass( "create directory" )

	def createDir(self, dialog, dirName ):
		if len(dirName)==0:
			return
		r = NetworkService.request(self.parent().parent().module,"add/node",{"node": self.parent().parent().node,"name":dirName}, secure=True, modifies=True, successHandler=self.onMkDir)
		r.dirName = dirName

	def onMkDir(self, req):
		dirName = req.dirName
		conf["mainWindow"].log("success",translate("Directory \"{name}\" created.", icon="icons-add-folder",name=dirName))

	def resetLoadingState(self):
		pass

actionDelegateSelector.insert( 3, AddNodeAction.isSuitableFor, AddNodeAction )


class EditAction(Button):
	"""
		Provides editing in a tree.simple application.
		If a directory is selected, it opens a dialog for renaming that directory,
		otherwise the full editWidget is used.
	"""
	def __init__(self, *args, **kwargs):
		super( EditAction, self ).__init__( translate("Edit"), icon="icons-edit", *args, **kwargs )
		self["class"] = "bar-item btn btn--small btn--edit"
		self["disabled"]= True
		self.isDisabled=True

	def onAttach(self):
		super(EditAction,self).onAttach()
		self.parent().parent().selectionChangedEvent.register( self )
		self.parent().parent().selectionActivatedEvent.register( self )

	def onDetach(self):
		self.parent().parent().selectionChangedEvent.unregister( self )
		self.parent().parent().selectionActivatedEvent.unregister( self )
		super(EditAction,self).onDetach()

	def onSelectionActivated(self, table, selection ):
		if not self.parent().parent().selectMode and len(selection)==1 and isinstance(selection[0], self.parent().parent().leafWidget):
			pane = Pane(translate("Edit"), closeable=True, iconClasses=["modul_%s" % self.parent().parent().module, "apptype_tree", "action_edit" ])
			conf["mainWindow"].stackPane( pane )
			skelType = "leaf"
			edwg = EditWidget( self.parent().parent().module, EditWidget.appTree, key=selection[0].data["key"], skelType=skelType)
			pane.addWidget( edwg )
			pane.focus()

	def onSelectionChanged(self, table, selection ):
		if len(selection)>0:
			if self.isDisabled:
				self.isDisabled = False
			self["disabled"]= False
		else:
			if not self.isDisabled:
				self["disabled"]= True
				self.isDisabled = True
	@staticmethod
	def isSuitableFor( module, handler, actionName ):
		if module is None or module not in conf["modules"].keys():
			return False

		correctAction = actionName=="edit"
		correctHandler = handler == "tree.simple" or handler.startswith("tree.simple.")
		hasAccess = conf["currentUser"] and ("root" in conf["currentUser"]["access"] or module+"-edit" in conf["currentUser"]["access"])
		isDisabled = module is not None and "disabledFunctions" in conf["modules"][module].keys() and conf["modules"][module]["disabledFunctions"] and "edit" in conf["modules"][module]["disabledFunctions"]

		return correctAction and correctHandler and hasAccess and not isDisabled

	def onClick(self, sender=None):
		selection = self.parent().parent().getCurrentSelection()
		if not selection:
			return

		for s in selection:
			if isinstance(s,self.parent().parent().nodeWidget):
				i = html5.ext.InputDialog(
					translate("Directory Name"),
					successHandler=self.editDir,
					value=s.data["name"]
				)
				i.dirKey = s.data["key"]
				return

			pane = Pane("Edit", closeable=True, iconClasses=["modul_%s" % self.parent().parent().module, "apptype_tree", "action_edit" ])
			conf["mainWindow"].stackPane( pane, focus=True )
			skelType = "leaf"
			edwg = EditWidget( self.parent().parent().module, EditWidget.appTree, key=s.data["key"], skelType=skelType)
			pane.addWidget( edwg )

	def editDir(self, dialog, dirName ):
		NetworkService.request( self.parent().parent().module, "edit/node", {"key": dialog.dirKey,"name": dirName}, secure=True, modifies=True)

	def resetLoadingState(self):
		pass

actionDelegateSelector.insert( 3, EditAction.isSuitableFor, EditAction )
