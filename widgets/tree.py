# -*- coding: utf-8 -*-
from vi import html5
import vi.utils as utils

from vi.network import NetworkService
from vi.widgets.actionbar import ActionBar
from vi.framework.event import EventDispatcher
from vi.priorityqueue import displayDelegateSelector, viewDelegateSelector, moduleHandlerSelector
from vi.config import conf
from vi.i18n import translate
from vi.framework.embedsvg import embedsvg

class _StructureWidget(html5.Li):

	def __init__(self, module, data, structure, *args, **kwargs):
		"""
			:param module: Name of the module for which we'll display data
			:type module: str
			:param data: The data we're going to display
			:type data: dict
			:param structure: The structure of that data as received from server
			:type structure: list
		"""
		super(_StructureWidget, self).__init__()

		self.module = module
		self.data = data
		self.structure = structure

		self.fromHTML("""
			<div class="item-image" [name]="nodeImage"></div>
			<div class="item-content" [name]="nodeContent">
				<div class="item-headline" [name]="nodeHeadline"></div>
				<div class="item-subline" [name]="nodeSubline"></div>
			</div>
			<div class="item-controls" [name]="nodeControls"></div>
		""")

		self.buildDescription()

		svg = embedsvg.get("icons-folder")
		if svg:
			nodeIcon = html5.I()
			nodeIcon.addClass("i")
			nodeIcon.element.innerHTML = svg + nodeIcon.element.innerHTML
			self.nodeImage.appendChild(nodeIcon)

		self["draggable"] = True

		self.sinkEvent("onDragOver", "onDrop", "onDragStart", "onDragLeave")

	def buildDescription(self):
		"""
			Creates the visual representation of our entry
		"""
		# Find any bones in the structure having "frontend_default_visible" set.
		hasDescr = False

		for boneName, boneInfo in self.structure:
			if "params" in boneInfo.keys() and isinstance(boneInfo["params"], dict):
				params = boneInfo["params"]
				if "frontend_default_visible" in params and params["frontend_default_visible"]:
					structure = {k: v for k, v in self.structure}
					wdg = viewDelegateSelector.select(self.module, boneName, structure)

					if wdg is not None:
						self.nodeHeadline.appendChild(wdg(self.module, boneName, structure).render(self.data, boneName))
						hasDescr = True

		# In case there is no bone configured for visualization, use a format-string
		if not hasDescr:
			format = "$(name)" #default fallback

			if self.module in conf["modules"].keys():
				moduleInfo = conf["modules"][self.module]
				if "format" in moduleInfo.keys():
					format = moduleInfo["format"]

			self.appendChild(html5.utils.unescape(
				utils.formatString(format, self.data, self.structure,
				    language=conf["currentlanguage"])))

class NodeWidget(_StructureWidget):
	"""
		Displays one Node (ie a directory) inside a TreeWidget
	"""

	def __init__(self, module, data, structure, *args, **kwargs):
		super(NodeWidget, self).__init__(module, data, structure, *args, **kwargs)
		self["class"] = "vi-tree-item vi-tree-node item has-hover is-drop-target is-draggable"
		self.sinkEvent("onDragOver", "onDrop", "onDragStart", "onDragLeave")

	def onDragOver(self, event):
		"""
			Check if we can handle the drag-data
		"""
		if not self.hasClass("insert-here"):
			self.addClass("insert-here")
			self["data-insert"] = translate("vi-data-insert")
		try:
			nodeType, srcKey = event.dataTransfer.getData("Text").split("/")
		except:
			return( super(NodeWidget,self).onDragOver(event) )

		event.preventDefault()
		event.stopPropagation()

	def onDragLeave(self, event):
		if self.hasClass("insert-here"):
			self.removeClass("insert-here")
			self["data-insert"] = None
		return( super(NodeWidget, self).onDragLeave(event))


	def onDragStart(self, event):
		"""
			Store our information in the drag's dataTransfer object
		"""
		event.dataTransfer.setData("Text", "node/" + self.data["key"])
		event.stopPropagation()

	def onDrop(self, event):
		"""
			Check if we can handle that drop and make the entries direct children of this node
		"""
		try:
			nodeType, srcKey = event.dataTransfer.getData("Text").split("/")
		except:
			return

		NetworkService.request(
			self.module, "move", {
				"skelType": nodeType,
				"key": srcKey,
				"destNode": self.data["key"]
			}, modifies=True, secure=True)

		event.preventDefault()
		event.stopPropagation()


class LeafWidget(_StructureWidget):
	"""
		Displays one Node (ie a file) inside a TreeWidget
	"""

	def __init__(self, module, data, structure, *args, **kwargs):
		"""
			:param module: Name of the module for which we'll display data
			:type module: str
			:param data: The data we're going to display
			:type data: dict
			:param structure: The structure of that data as received from server
			:type structure: list
		"""
		super(LeafWidget, self).__init__(module, data, structure, *args, **kwargs)
		self.module = module
		self.data = data
		self.structure = structure

		self.fromHTML("""
			<div class="item-image" [name]="leafImage"></div>
			<div class="item-content" [name]="leafContent">
				<div class="item-headline" [name]="leafHeadline"></div>
				<div class="item-subline" [name]="leafSubline"></div>
			</div>
			<div class="item-controls" [name]="leafControls"></div>
		""")

		self.buildDescription()
		self["class"] = "vi-tree-item vi-tree-leaf item has-hover is-draggable"
		self["draggable"] = True
		self.sinkEvent("onDragStart")

	def onDragStart(self, event):
		"""
			Store our information in the drag's dataTransfer object
		"""
		event.dataTransfer.setData("Text", "leaf/" + self.data["key"])
		event.stopPropagation()


class SelectionContainer(html5.Ul):
	"""
		Provides a Container, which allows selecting its contents.
		Designed to be used within a tree widget, as it distinguishes between
		two different types of content (nodes and leafs) and allows selections to
		be restricted to a certain kind.
	"""
	def __init__(self, nodeWidget, leafWidget, selectionType="both", multiSelection=False, *args, **kwargs ):
		super(SelectionContainer, self ).__init__(*args, **kwargs)
		self.addClass("vi-tree-selectioncontainer", "vi-selectioncontainer", "list")
		self["title"] = translate("vi.tree.drag-here")
		self["tabindex"] = 1
		self.selectionType = selectionType
		self.multiSelection = multiSelection
		self.nodeWidget = nodeWidget
		self.leafWidget = leafWidget
		self.selectionChangedEvent = EventDispatcher("selectionChanged")
		self.selectionActivatedEvent = EventDispatcher(
			"selectionActivated")  # Double-Click on an currently selected item - ITEM CLICKED !!!!
		self.selectionReturnEvent = EventDispatcher(
			"selectionReturn")  # The current selection should be returned to parent widget
		self.cursorMovedEvent = EventDispatcher("cursorMoved")
		self._selectedItems = []  # List of row-indexes currently selected
		self._currentItem = None  # Rowindex of the cursor row
		self._isMouseDown = False  # Tracks status of the left mouse button
		self._isCtlPressed = False  # Tracks status of the ctrl key
		self._ctlStartRow = None  # Stores the row where a multi-selection (using the ctrl key) started
		self.sinkEvent("onClick", "onDblClick", "onMouseMove", "onMouseDown", "onMouseUp", "onKeyDown", "onKeyUp")

	def setCurrentItem(self, item):
		"""
			Sets the  currently selected item (=the cursor) to 'item'
			If there was such an item before, its unselected afterwards.
		"""
		if self._currentItem:
			self._currentItem.removeClass("is-focused")
		self._currentItem = item
		if item:
			item.addClass("is-focused")

	def onClick(self, event):
		self.focus()
		for child in self._children:
			if html5.utils.doesEventHitWidgetOrChildren(event, child):
				self.setCurrentItem(child)
				if self._isCtlPressed:
					self.addSelectedItem(child)
		if not self._isCtlPressed:
			self.clearSelection()
		if self._selectedItems:
			self.selectionChangedEvent.fire(self, self._selectedItems[:])
		elif self._currentItem:
			self.selectionChangedEvent.fire(self, [self._currentItem])
		else:
			self.selectionChangedEvent.fire(self, [])

	def onDblClick(self, event):
		for child in self.children():

			if html5.utils.doesEventHitWidgetOrChildren(event, child):
				if self.selectionType == "node" and isinstance(child, self.nodeWidget) or \
					self.selectionType == "leaf" and isinstance(child, self.leafWidget) or \
					self.selectionType == "both":

					self.selectionActivatedEvent.fire(self, [child])
					break

	def activateCurrentSelection(self):
		"""
			Emits the selectionActivated event if there's currently a selection

		"""
		if len(self._selectedItems) > 0:
			self.selectionActivatedEvent.fire(self, self._selectedItems)

		elif self._currentItem is not None:
			self.selectionActivatedEvent.fire(self, [self._currentItem])

	def returnCurrentSelection(self):
		"""
			Emits the selectionReturn event if there's currently a selection

		"""
		selection = []
		if len(self._selectedItems) > 0:
			selection = self._selectedItems
		# self.selectionReturnEvent.fire( self, self._selectedItems )
		elif self._currentItem is not None:
			selection = [self._currentItem]
		if self.selectionType == "node":
			selection = [x for x in selection if isinstance(x, self.nodeWidget)]
		elif self.selectionType == "leaf":
			selection = [x for x in selection if isinstance(x, self.leafWidget)]
		self.selectionReturnEvent.fire(self, selection)

	def onKeyDown(self, event):
		if html5.isReturn(event):  # Return
			self.activateCurrentSelection()
			event.preventDefault()
			return
		elif html5.isControl(event):  # and "multi" in (self.selectMode or ""): #Ctrl
			self._isCtlPressed = True

	def onKeyUp(self, event):
		if html5.isControl(event):
			self._isCtlPressed = False

	def clearSelection(self):
		for child in self._children[:]:
			self.removeSelectedItem(child)

	def addSelectedItem(self, item):
		# if not self.multiSelection:
		#	return
		if self.selectionType == "node" and isinstance(item, self.nodeWidget) or \
			self.selectionType == "leaf" and isinstance(item, self.leafWidget) or \
			self.selectionType == "both":
			if not item in self._selectedItems:
				self._selectedItems.append( item )
				item.addClass("is-selected")


	def removeSelectedItem(self, item):
		if not item in self._selectedItems:
			return

		self._selectedItems.remove( item )
		item.removeClass("is-selected")


	def clear(self):
		self.clearSelection()
		for child in self._children[:]:
			self.removeChild(child)
		self.selectionChangedEvent.fire(self, [])

	def getCurrentSelection(self):
		if len(self._selectedItems) > 0:
			return self._selectedItems[:]
		if self._currentItem:
			return [self._currentItem]
		return None


class TreeWidget(html5.Div):
	nodeWidget = NodeWidget
	leafWidget = LeafWidget
	defaultActions = ["add.node", "add.leaf", "selectrootnode", "edit", "delete", "reload"]

	def __init__(self, module, rootNode=None, node=None, selectMode=None, *args, **kwargs):
		"""
			:param module: Name of the module we shall handle. Must be a list application!
			:type module: str
			:param rootNode: The rootNode we shall display. If None, we try to select one.
			:type rootNode: str or None
			:param node: The node we shall display at start. Must be a child of rootNode
			:type node: str or None
		"""

		super( TreeWidget, self ).__init__( )
		self.addClass("vi-widget vi-widget--tree vi-tree")

		self.module = module
		self.rootNode = rootNode
		self.node = node or rootNode
		self.actionBar = ActionBar(module, "tree")
		self.appendChild(self.actionBar)
		self.pathList = html5.Div()

		self.pathList.addClass("vi-tree-breadcrumb")
		self.appendChild(self.pathList)

		self.entryFrame = SelectionContainer(self.nodeWidget, self.leafWidget)
		self.appendChild(self.entryFrame)
		self.entryFrame.selectionActivatedEvent.register(self)
		self._batchSize = 99
		self._currentCursor = {"node": None, "leaf": None}
		self._currentRequests = []
		self.rootNodeChangedEvent = EventDispatcher("rootNodeChanged")
		self.nodeChangedEvent = EventDispatcher("nodeChanged")

		assert selectMode in [None, "single", "multi", "single.leaf", "single.node", "multi.leaf", "multi.node"]
		self.selectMode = selectMode

		if self.rootNode:
			self.reloadData()
			self.rebuildPath()
		else:
			NetworkService.request(self.module, "listRootNodes", successHandler=self.onSetDefaultRootNode)

		self.sinkEvent("onClick")

		# Proxy some events and functions of the original table
		for f in ["selectionChangedEvent", "selectionActivatedEvent", "cursorMovedEvent", "getCurrentSelection",
				  "selectionReturnEvent"]:
			setattr(self, f, getattr(self.entryFrame, f))

		self.actionBar.setActions(self.defaultActions + (["select", "close"] if self.selectMode else []))

	def showErrorMsg(self, req=None, code=None):
		"""
			Removes all currently visible elements and displays an error message
		"""
		self.actionBar["style"]["display"] = "none"
		self.entryFrame["style"]["display"] = "none"
		errorDiv = html5.Div()

		errorDiv.addClass("popup popup--center msg msg--error is-active")
		if code and (code==401 or code==403):
			txt = "Access denied!"
		else:
			txt = "An unknown error occurred!"
		errorDiv.addClass("error_code_%s" % (code or 0))
		errorDiv.appendChild( html5.TextNode( txt ) )
		self.appendChild( errorDiv )


	def onAttach(self):
		super(TreeWidget, self).onAttach()
		NetworkService.registerChangeListener(self)

	def onDetach(self):
		super(TreeWidget, self).onDetach()
		NetworkService.removeChangeListener(self)

	def onDataChanged(self, module, **kwargs):
		if module != self.module:

			isRootNode = False
			for k, v in conf["modules"].items():
				if (k == module
					and v.get("handler") == "list"
					and v.get("rootNodeOf") == self.module):
					isRootNode = True
					break

			if not isRootNode:
				return

		if "selectrootnode" in self.actionBar.widgets.keys():
			self.actionBar.widgets["selectrootnode"].update()

		self.reloadData()

	def onSelectionActivated(self, div, selection):
		if not selection:
			return

		item = selection[0]

		if isinstance(item, self.nodeWidget):
			self.setNode(item.data["key"])

		elif isinstance(item, self.leafWidget) and "leaf" in (self.selectMode or ""):
			self.returnCurrentSelection()

	def activateCurrentSelection(self):
		return self.entryFrame.activateCurrentSelection()

	def returnCurrentSelection(self):
		conf["mainWindow"].removeWidget(self)
		return self.entryFrame.returnCurrentSelection()

	def onClick(self, event):
		super(TreeWidget, self).onClick(event)
		for c in self.pathList._children:
			# Test if the user clicked inside the path-list
			if html5.utils.doesEventHitWidgetOrParents(event, c):
				self.setNode(c.data["key"])
				return

	def onSetDefaultRootNode(self, req):
		data = NetworkService.decode(req)
		if len(data) > 0:
			self.setRootNode(data[0]["key"], self.node)

	def setRootNode(self, rootNode, node=None):
		self.rootNode = rootNode
		self.node = node or rootNode
		self.rootNodeChangedEvent.fire(rootNode)
		if node:
			self.nodeChangedEvent.fire(node)
		self.reloadData()
		self.rebuildPath()

	def setNode(self, node):
		self.node = node
		self.nodeChangedEvent.fire(node)
		self.reloadData()
		self.rebuildPath()

	def rebuildPath(self):
		"""
			Rebuild the displayed path-list.
		"""
		self.pathList.removeAllChildren()

		NetworkService.request(
			self.module, "view/node/%s" % self.node,
			successHandler=self.onPathRequestSucceded
		)

	def onPathRequestSucceded(self, req):
		"""
			Rebuild the displayed path-list according to request data
		"""
		answ = NetworkService.decode(req)
		skel = answ["values"]

		if skel["parentdir"] and skel["parentdir"] != skel["key"]:
			c = NodeWidget(self.module, skel, [])

			NetworkService.request(
				self.module, "view/node/%s" % skel["parentdir"],
				successHandler=self.onPathRequestSucceded
			)

		else:
			c = NodeWidget(self.module, {"key": self.rootNode, "name": "root"}, [])
			c.addClass("is-rootnode")

		self.pathList.prependChild(c)


	def reloadData(self, paramsOverride=None):
		assert self.node is not None, "reloadData called while self.node is None"
		self.entryFrame.clear()
		self._currentRequests = []
		if paramsOverride:
			params = paramsOverride.copy()
		else:
			params = {"node": self.node}

		if "amount" not in params:
			params["amount"] = self._batchSize

		r = NetworkService.request(self.module, "list/node", params,
								   successHandler=self.onRequestSucceded,
								   failureHandler=self.showErrorMsg)
		r.reqType = "node"
		self._currentRequests.append(r)
		r = NetworkService.request(self.module, "list/leaf", params,
								   successHandler=self.onRequestSucceded,
								   failureHandler=self.showErrorMsg)
		r.reqType = "leaf"
		self._currentRequests.append(r)

		from vi.handler.tree import TreeHandler # import must be here, otherwise it throws an importError
		if isinstance(conf["mainWindow"].currentPane, TreeHandler):
			conf["theApp"].setPath(self.module + "/list/" + self.node)

	def onRequestSucceded(self, req):
		if not req in self._currentRequests:
			return

		self._currentRequests.remove(req)
		data = NetworkService.decode(req)

		for skel in data["skellist"]:
			if req.reqType == "node":
				n = self.nodeWidget(self.module, skel, data["structure"])
			else:
				n = self.leafWidget(self.module, skel, data["structure"])

			self.entryFrame.appendChild(n)

		self.entryFrame.sortChildren(self.getChildKey)

		if "cursor" in data.keys() and len(data["skellist"]) == req.params["amount"]:
			self._currentCursor[req.reqType] = data["cursor"]

			req.params["cursor"] = data["cursor"]
			r = NetworkService.request(self.module, "list/%s" % req.reqType, req.params,
									   successHandler=self.onRequestSucceded,
									   failureHandler=self.showErrorMsg)
			r.reqType = req.reqType
			self._currentRequests.append(r)
		else:
			self._currentCursor[req.reqType] = None

		self.actionBar.resetLoadingState()

	def getChildKey(self, widget):
		"""
			Derives a string used to sort the entries in our entryframe
		"""
		name = (widget.data.get("name") or "").lower()

		if isinstance(widget, self.nodeWidget):
			return "0-%s" % name
		elif isinstance(widget, self.leafWidget):
			return "1-%s" % name
		else:
			return "2-"

	@staticmethod
	def canHandle(moduleName, moduleInfo):
		return moduleInfo["handler"].startswith("tree.")

	@staticmethod
	def render(moduleName, adminInfo, context):
		rootNode = context.get(conf["vi.context.prefix"] + "rootNode") if context else None
		return TreeWidget(module=moduleName, rootNode=rootNode, context=context)


displayDelegateSelector.insert(1, TreeWidget.canHandle, TreeWidget)
moduleHandlerSelector.insert(1, TreeWidget.canHandle, TreeWidget.render)
