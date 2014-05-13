# -*- coding: utf-8 -*-

import html5
from html5.a import A
from html5.form import Fieldset
from network import NetworkService
from config import conf
from priorityqueue import editBoneSelector
from widgets.tooltip import ToolTip
from priorityqueue import protocolWrapperInstanceSelector
from widgets.actionbar import ActionBar
import utils
from i18n import translate
class InvalidBoneValueException(ValueError):
	pass


class InternalEdit( html5.Div ):

	def __init__(self, skelStructure, values=None, errorInformation=None ):
		super( InternalEdit, self ).__init__()
		self.editIdx = 1
		self.skelStructure = skelStructure
		self.values = values
		self.errorInformation = errorInformation
		self.form = html5.Form()
		self.appendChild(self.form)
		self.renderStructure()
		if values:
			self.unserialize( values )


	def renderStructure(self):
		#Clear the UI
		#self.clear()
		self.bones = {}
		#self.actionbar.resetLoadingState()
		#self.dataCache = data
		tmpDict = utils.boneListToDict( self.skelStructure )
		fieldSets = {}
		currRow = 0
		hasMissing = False
		for key, bone in self.skelStructure:
			if bone["visible"]==False:
				continue
			cat = "default"
			if "params" in bone.keys() and isinstance(bone["params"],dict) and "category" in bone["params"].keys():
				cat = bone["params"]["category"]
			if not cat in fieldSets.keys():
				fs = html5.Fieldset()
				fs["class"] = cat
				if cat=="default":
					fs["class"].append("active")
				#fs["id"] = "vi_%s_%s_%s_%s" % (self.editIdx, self.modul, "edit" if self.key else "add", cat)
				fs["name"] = cat
				legend = html5.Legend()
				#legend["id"] = "vi_%s_%s_%s_%s_legend" % (self.editIdx,self.modul, "edit" if self.key else "add", cat)
				fshref = fieldset_A()
				#fshref["href"] = "#vi_%s_%s_%s_%s" % (self.editIdx, self.modul, "edit" if self.key else "add", cat)
				fshref.appendChild(html5.TextNode(cat) )
				legend.appendChild( fshref )
				fs.appendChild(legend)
				section = html5.Section()
				fs.appendChild(section)
				fs._section = section
				fieldSets[ cat ] = fs
			if "params" in bone.keys() and bone["params"] and "category" in bone["params"].keys():
				tabName = bone["params"]["category"]
			else:
				tabName = "Test"#QtCore.QCoreApplication.translate("EditWidget", "General")
			wdgGen = editBoneSelector.select( None, key, tmpDict )
			widget = wdgGen.fromSkelStructure( None, key, tmpDict )
			widget["id"] = "vi_%s_%s_%s_%s_bn_%s" % (self.editIdx, None, "internal", cat, key)
			#widget["class"].append(key)
			#widget["class"].append(bone["type"].replace(".","_"))
			#self.prepareCol(currRow,1)
			descrLbl = html5.Label(bone["descr"])
			descrLbl["class"].append(key)
			descrLbl["class"].append(bone["type"].replace(".","_"))
			descrLbl["for"] = "vi_%s_%s_%s_%s_bn_%s" % ( self.editIdx, None, "internal", cat, key)
			if bone["required"]:
				descrLbl["class"].append("is_required")
			if bone["required"] and (bone["error"] is not None or (self.errorInformation and key in self.errorInformation.keys())):
				descrLbl["class"].append("is_invalid")
				if bone["error"]:
					descrLbl["title"] = bone["error"]
				else:
					descrLbl["title"] = self.errorInformation[ key ]
				fieldSets[ cat ]["class"].append("is_incomplete")
				hasMissing = True
			if bone["required"] and not (bone["error"] is not None or (self.errorInformation and key in self.errorInformation.keys())):
				descrLbl["class"].append("is_valid")
			if "params" in bone.keys() and isinstance(bone["params"], dict) and "tooltip" in bone["params"].keys():
				tmp = html5.Span()
				tmp.appendChild(descrLbl)
				tmp.appendChild( ToolTip(longText=bone["params"]["tooltip"]) )
				descrLbl = tmp
			containerDiv = html5.Div()
			containerDiv.appendChild( descrLbl )
			containerDiv.appendChild( widget )
			fieldSets[ cat ]._section.appendChild( containerDiv )
			containerDiv["class"].append("bone")
			containerDiv["class"].append("bone_"+key)
			containerDiv["class"].append( bone["type"].replace(".","_") )
			if "." in bone["type"]:
				for t in bone["type"].split("."):
					containerDiv["class"].append(t)
			#self["cell"][currRow][0] = descrLbl
			#fieldSets[ cat ].appendChild( widget )
			#self["cell"][currRow][1] = widget
			currRow += 1
			self.bones[ key ] = widget
		if len(fieldSets)==1:
			for (k,v) in fieldSets.items():
				if not "active" in v["class"]:
					v["class"].append("active")
		tmpList = [(k,v) for (k,v) in fieldSets.items()]
		tmpList.sort( key=lambda x:x[0])
		for k,v in tmpList:
			self.form.appendChild( v )
			v._section = None


	def doSave( self, closeOnSuccess=False, *args, **kwargs ):
		"""
			Starts serializing and transmitting our values to the server.
		"""
		self.closeOnSuccess = closeOnSuccess
		res = {}
		for key, bone in self.bones.items():
			try:
				res.update( bone.serializeForPost( ) )
			except InvalidBoneValueException:
				#Fixme: Bad hack..
				lbl = bone.parent()._children[0]
				if "is_valid" in lbl["class"]:
					lbl["class"].remove("is_valid")
				lbl["class"].append("is_invalid")
				self.actionbar.resetLoadingState()
				return
		return( res )

	def unserialize(self, data):
		"""
			Applies the actual data to the bones.
		"""
		for bone in self.bones.values():
			bone.unserialize( data )

def parseHashParameters( src, prefix="" ):
	"""
		Converts a flat dictionary containing dotted properties into a multi-dimensional one.

		Example:
			{ "a":"a", "b.a":"ba","b.b":"bb" } -> { "a":"a", "b":{"a":"ba","b":"bb"} }
	"""

	res = {}
	processedPrefixes = [] #Dont process a prefix twice
	for k,v in src.items():
		if prefix and not k.startswith( prefix ):
			continue
		if prefix:
			k = k.replace(prefix,"")
		if not "." in k:
			res[ k ] = v
		else:
			newPrefix = k[ :k.find(".")  ]
			if newPrefix in processedPrefixes: #We did this allready
				continue
			processedPrefixes.append( newPrefix )
			res[ newPrefix ] = parseHashParameters( src, prefix="%s%s." %(prefix,newPrefix))
	return( res )


class EditWidget( html5.Div ):
	appList = "list"
	appHierarchy = "hierarchy"
	appTree = "tree"
	appSingleton = "singleton"
	__editIdx_ = 0 #Internal counter to ensure unique ids

	def __init__(self, modul, applicationType, key=0, node=None, skelType=None, clone=False, hashArgs=None, *args, **kwargs ):
		"""
			Initialize a new Edit or Add-Widget for the given modul.
			@param modul: Name of the modul
			@type modul: String
			@param applicationType: Defines for what application this Add / Edit should be created. This hides additional complexity introduced by the hierarchy / tree-application
			@type applicationType: Any of EditWidget.appList, EditWidget.appHierarchy, EditWidget.appTree or EditWidget.appSingleton
			@param id: ID of the entry. If none, it will add a new Entry.
			@type id: Number
			@param rootNode: If applicationType==EditWidget.appHierarchy, the new entry will be added under this node, if applicationType==EditWidget,appTree the final node is derived from this and the path-parameter. 
			Has no effect if applicationType is not appHierarchy or appTree or if an id have been set.
			@type rootNode: String
			@param path: Specifies the path from the rootNode for new entries in a treeApplication
			@type path: String
			@param clone: If true, it will load the values from the given id, but will save a new entry (i.e. allows "cloning" an existing entry)
			@type clone: Bool
			@param hashArgs: Dictionary of parameters (usually supplied by the window.hash property) which should prefill values.
			@type hashArgs: Dict
		"""
		super( EditWidget, self ).__init__( *args, **kwargs )
		self.modul = modul
		# A Bunch of santy-checks, as there is a great chance to mess around with this widget
		assert applicationType in [ EditWidget.appList, EditWidget.appHierarchy, EditWidget.appTree, EditWidget.appSingleton ] #Invalid Application-Type?
		if applicationType==EditWidget.appHierarchy or applicationType==EditWidget.appTree:
			assert id is not None or node is not None #Need either an id or an node
		if clone:
			assert id is not None #Need an id if we should clone an entry
			assert not applicationType==EditWidget.appSingleton # We cant clone a singleton
			if applicationType==EditWidget.appHierarchy or applicationType==EditWidget.appTree:
				assert node is not None #We still need a rootNode for cloning
			if applicationType==EditWidget.appTree:
				assert node is not None #We still need a path for cloning #FIXME
		# End santy-checks
		self.editIdx = EditWidget.__editIdx_ #Iternal counter to ensure unique ids
		EditWidget.__editIdx_ += 1
		self.applicationType = applicationType
		self.key = key
		self.node = node
		self.skelType = skelType
		self.clone = clone
		self.bones = {}
		self.closeOnSuccess = False
		self._lastData = {} #Dict of structure and values received
		if hashArgs:
			self._hashArgs = parseHashParameters( hashArgs )
			warningNode = html5.TextNode("Warning: Values shown below got overriden by the Link you clicked on and do NOT represent the actual values!\n"+\
						"Doublecheck them before saving!")
			warningSpan = html5.Span()
			warningSpan["class"].append("warning")
			warningSpan.appendChild( warningNode )
			self.appendChild( warningSpan )
		else:
			self._hashArgs = None
		self.editTaskID = None
		self.wasInitialRequest = True #Wherever the last request attempted to save data or just fetched the form
		self.actionbar = ActionBar( self.modul, self.applicationType, "edit" if self.key else "add" )
		self.appendChild( self.actionbar )
		self.form = html5.Form()
		self.appendChild(self.form)
		self.actionbar.setActions(["save.close","save.continue","reset"])
		self.reloadData( )

	def showErrorMsg(self, req=None, code=None):
		"""
			Removes all currently visible elements and displayes an error message
		"""
		self.actionbar["style"]["display"] = "none"
		self.form["style"]["display"] = "none"
		errorDiv = html5.Div()
		errorDiv["class"].append("error_msg")
		if code and (code==401 or code==403):
			txt = translate("Access denied!")
		else:
			txt = translate("An unknown error occurred!")
		errorDiv["class"].append("error_code_%s" % (code or 0))
		errorDiv.appendChild( html5.TextNode( txt ) )
		self.appendChild( errorDiv )

	def reloadData(self):
		self.save( {} )
		return

	def save(self, data ):
		"""
			Creates the actual NetworkService request used to transmit our data.
			If data is None, it fetches a clean add/edit form.

			@param data: The values to transmit or None to fetch a new, clean add/edit form.
			@type data: Dict or None
		"""
		self.wasInitialRequest = not len(data)>0
		if self.modul=="_tasks":
			#self.editTaskID = protoWrap.edit( self.key, **data )
			#request = NetworkService.request("/%s/execute/%s" % ( self.modul, self.id ), data, secure=True, successHandler=self.onSaveResult )
			return #FIXME!
		elif self.applicationType == EditWidget.appList: ## Application: List
			if self.key and (not self.clone or not data):
				#self.editTaskID = protoWrap.edit( self.key, **data )
				NetworkService.request(self.modul,"edit/%s" % self.key, data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg)
			else:
				NetworkService.request(self.modul, "add", data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg )
				#self.editTaskID = protoWrap.add( **data )
		elif self.applicationType == EditWidget.appHierarchy: ## Application: Hierarchy
			if self.key and not self.clone:
				NetworkService.request(self.modul,"edit/%s" % self.key, data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg)
				#self.editTaskID = protoWrap.edit( self.key, **data )
			else:
				NetworkService.request(self.modul, "add/%s" % self.node, data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg )
				#self.editTaskID = protoWrap.add( self.node, **data )
		elif self.applicationType == EditWidget.appTree: ## Application: Tree
			if self.key and not self.clone:
				NetworkService.request(self.modul,"edit/%s/%s" % (self.skelType,self.key), data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg)
				#self.editTaskID = protoWrap.edit( self.key, self.skelType, **data )
			else:
				NetworkService.request(self.modul,"add/%s/%s" % (self.skelType,self.node), data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg)
				#self.editTaskID = protoWrap.add( self.node, self.skelType, **data )
		elif self.applicationType == EditWidget.appSingleton: ## Application: Singleton
			#self.editTaskID = protoWrap.edit( **data )
			NetworkService.request(self.modul,"edit", data, secure=len(data)>0, successHandler=self.setData, failureHandler=self.showErrorMsg)
		else:
			raise NotImplementedError() #Should never reach this

	def clear(self):
		"""
			Removes all visible bones/forms/fieldsets.
		"""
		for c in self.form._children[ : ]:
			self.form.removeChild( c )

	def setData( self, request=None, data=None, ignoreMissing=False ):
		"""
		Rebuilds the UI according to the skeleton received from server

		@param request: A finished NetworkService request
		@type request: NetworkService
		@type data: dict
		@param data: The data received
		"""
		assert (request or data)
		if request:
			data = NetworkService.decode( request )
		if "action" in data and (data["action"] == "addSuccess" or data["action"] == "editSuccess"):
			NetworkService.notifyChange(self.modul)
			logDiv = html5.Div()
			logDiv["class"].append("msg")
			spanMsg = html5.Span()
			spanMsg.appendChild( html5.TextNode( translate("Entry saved!") ))
			spanMsg["class"].append("msgspan")
			logDiv.appendChild(spanMsg)
			if self.modul in conf["modules"].keys():
				spanMsg = html5.Span()
				spanMsg.appendChild( html5.TextNode( conf["modules"][self.modul]["name"] ))
				spanMsg["class"].append("modulspan")
				logDiv.appendChild(spanMsg)
			if "values" in data.keys() and "name" in data["values"].keys():
				spanMsg = html5.Span()
				spanMsg.appendChild( html5.TextNode( str(data["values"]["name"]) ))
				spanMsg["class"].append("namespan")
				logDiv.appendChild(spanMsg)
			conf["mainWindow"].log("success",logDiv)
			if self.closeOnSuccess:
				conf["mainWindow"].removeWidget( self )
				return
			self.clear()
			self.bones = {}
			self.reloadData()
			return
		#Clear the UI
		self.clear()
		self.bones = {}
		self.actionbar.resetLoadingState()
		self.dataCache = data
		tmpDict = utils.boneListToDict( data["structure"] )
		fieldSets = {}
		currRow = 0
		hasMissing = False
		for key, bone in data["structure"]:
			if bone["visible"]==False:
				continue
			cat = "default"
			if "params" in bone.keys() and isinstance(bone["params"],dict) and "category" in bone["params"].keys():
				cat = bone["params"]["category"]
			if not cat in fieldSets.keys():
				fs = html5.Fieldset()
				fs["class"] = cat
				if cat=="default":
					fs["class"].append("active")
				#fs["id"] = "vi_%s_%s_%s_%s" % (self.editIdx, self.modul, "edit" if self.key else "add", cat)
				fs["name"] = cat
				legend = html5.Legend()
				#legend["id"] = "vi_%s_%s_%s_%s_legend" % (self.editIdx,self.modul, "edit" if self.key else "add", cat)
				fshref = fieldset_A()
				#fshref["href"] = "#vi_%s_%s_%s_%s" % (self.editIdx, self.modul, "edit" if self.key else "add", cat)
				fshref.appendChild(html5.TextNode(cat) )
				legend.appendChild( fshref )
				fs.appendChild(legend)
				section = html5.Section()
				fs.appendChild(section)
				fs._section = section
				fieldSets[ cat ] = fs
			if "params" in bone.keys() and bone["params"] and "category" in bone["params"].keys():
				tabName = bone["params"]["category"]
			else:
				tabName = "Test"#QtCore.QCoreApplication.translate("EditWidget", "General")
			wdgGen = editBoneSelector.select( self.modul, key, tmpDict )
			widget = wdgGen.fromSkelStructure( self.modul, key, tmpDict )
			widget["id"] = "vi_%s_%s_%s_%s_bn_%s" % (self.editIdx, self.modul, "edit" if self.key else "add", cat, key)
			#widget["class"].append(key)
			#widget["class"].append(bone["type"].replace(".","_"))
			#self.prepareCol(currRow,1)
			descrLbl = html5.Label(bone["descr"])
			descrLbl["class"].append(key)
			descrLbl["class"].append(bone["type"].replace(".","_"))
			descrLbl["for"] = "vi_%s_%s_%s_%s_bn_%s" % ( self.editIdx, self.modul, "edit" if self.key else "add", cat, key)
			if bone["required"]:
				descrLbl["class"].append("is_required")
			if bone["required"] and bone["error"] is not None:
				descrLbl["class"].append("is_invalid")
				descrLbl["title"] = bone["error"]
				fieldSets[ cat ]["class"].append("is_incomplete")
				hasMissing = True
			if bone["required"] and bone["error"] is None and not self.wasInitialRequest:
				descrLbl["class"].append("is_valid")
			if isinstance(bone["error"], dict):
				widget.setExtendedErrorInformation( bone["error"] )
			if "params" in bone.keys() and isinstance(bone["params"], dict) and "tooltip" in bone["params"].keys():
				tmp = html5.Span()
				tmp.appendChild(descrLbl)
				tmp.appendChild( ToolTip(longText=bone["params"]["tooltip"]) )
				descrLbl = tmp
			containerDiv = html5.Div()
			containerDiv.appendChild( descrLbl )
			containerDiv.appendChild( widget )
			fieldSets[ cat ]._section.appendChild( containerDiv )
			containerDiv["class"].append("bone")
			containerDiv["class"].append("bone_"+key)
			containerDiv["class"].append( bone["type"].replace(".","_") )
			if "." in bone["type"]:
				for t in bone["type"].split("."):
					containerDiv["class"].append(t)
			#self["cell"][currRow][0] = descrLbl
			#fieldSets[ cat ].appendChild( widget )
			#self["cell"][currRow][1] = widget
			currRow += 1
			self.bones[ key ] = widget
		if len(fieldSets)==1:
			for (k,v) in fieldSets.items():
				if not "active" in v["class"]:
					v["class"].append("active")
		tmpList = [(k,v) for (k,v) in fieldSets.items()]
		tmpList.sort( key=lambda x:x[0])
		for k,v in tmpList:
			self.form.appendChild( v )
			v._section = None
		self.unserialize( data["values"] )
		if self._hashArgs: #Apply the default values (if any)
			self.unserialize( self._hashArgs )
			self._hashArgs = None
		self._lastData = data
		if hasMissing and not self.wasInitialRequest:
			conf["mainWindow"].log("warning",translate("Could not save entry!"))

	def unserialize(self, data):
		"""
			Applies the actual data to the bones.
		"""
		for bone in self.bones.values():
			bone.unserialize( data )

	def doSave( self, closeOnSuccess=False, *args, **kwargs ):
		"""
			Starts serializing and transmitting our values to the server.
		"""
		self.closeOnSuccess = closeOnSuccess
		res = {}
		for key, bone in self.bones.items():
			try:
				res.update( bone.serializeForPost( ) )
			except InvalidBoneValueException:
				#Fixme: Bad hack..
				lbl = bone.parent()._children[0]
				if "is_valid" in lbl["class"]:
					lbl["class"].remove("is_valid")
				lbl["class"].append("is_invalid")
				self.actionbar.resetLoadingState()
				return
		self.save( res )

class fieldset_A(A):
	_baseClass = "a"

	def __init__(self, *args, **kwargs):
		super(fieldset_A,self).__init__(*args, **kwargs )
		self.sinkEvent("onClick")

	def onClick(self,event):
		for element in self.parent().parent().parent()._children:
			if isinstance(element,Fieldset):
				if utils.doesEventHitWidgetOrChildren( event, element ):
					if not "active" in element["class"]:
						element["class"].append("active")
						element["class"].remove("inactive")
					else:
						if not "inactive" in element["class"]:
							element["class"].append("inactive")
						element["class"].remove("active")
				else:
					if not "inactive" in element["class"] and isinstance(element,fieldset_A):
						element["class"].append("inactive")
					element["class"].remove("active")
					if len(element._children)>0 and isinstance(element,fieldset_A) and hasattr(element._children[1],"_children"): #subelement crawler
						for sube in element._children[1]._children:
							if isinstance(sube,fieldset_A):
								if not "inactive" in sube["class"]:
									sube.parent["class"].append("inactive")
								sube["class"].remove("active")