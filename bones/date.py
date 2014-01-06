#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import html5
from priorityqueue import editBoneSelector, viewDelegateSelector
from datetime import datetime
import re

class DateViewBoneDelegate( object ):
	def __init__(self, modulName, boneName, skelStructure, *args, **kwargs ):
		super( DateViewBoneDelegate, self ).__init__()
		self.skelStructure = skelStructure
		self.boneName = boneName
		self.modulName=modulName

	def render( self, data, field ):
		if field in data.keys():
			return( html5.Label(str( data[field])))
		return( html5.Label("..") )

class DateEditBone( html5.Div ):
	def __init__(self, modulName, boneName,readOnly,date=True, time=True, *args, **kwargs ):
		super( DateEditBone,  self ).__init__( *args, **kwargs )
		self.boneName = boneName
		self.readOnly = readOnly
		self.hasdate =date
		self.hastime =time
		if date:
			self.dateinput=html5.Input()
			self.dateinput["type"]="date"
			self.dateinput["style"]["float"]="left"
			self.appendChild(self.dateinput)
		if time:
			self.timeinput=html5.Input()
			self.timeinput["type"]="time"
			self.timeinput["style"]["float"]="left"
			self.timeinput["style"]["width"]="70px"
			self.appendChild(self.timeinput)

	@staticmethod
	def fromSkelStructure( modulName, boneName, skelStructure ):
		readOnly = "readonly" in skelStructure[ boneName ].keys() and skelStructure[ boneName ]["readonly"]
		date = skelStructure[ boneName ]["date"] if "date" in skelStructure[ boneName ].keys() else True
		time = skelStructure[ boneName ]["time"] if "time" in skelStructure[ boneName ].keys() else True
		return( DateEditBone( modulName, boneName, readOnly,date,time ) )

	def unserialize(self, data):
		if self.boneName in data.keys():
			if self.hastime and not self.hasdate:
				self.timeinput["value"]=data[ self.boneName ]
			if self.hasdate  and not self.hastime:
				dateobj=datetime.strptime(data[ self.boneName ], "%d.%m.%Y")
				self.dateinput["value"]=dateobj.strftime( "%Y-%m-%d" )
			if self.hasdate  and self.hastime:
				dateobj=datetime.strptime(data[ self.boneName ], "%d.%m.%Y %H:%M:%S")
				self.dateinput["value"]=dateobj.strftime( "%Y-%m-%d" )
				self.timeinput["value"]=dateobj.strftime( "%H:%M:%S" )


	def serializeForPost(self):
		#[day, month, year, hour, min,sec]
		adatetime=["00","00","0000","00","00","00"]

		if hasattr(self,"timeinput"):
			result = re.match('(\d+):(\d+)',self.timeinput["value"])
			if result:
				adatetime[3] = result.group(1)
				adatetime[4] = result.group(2)
		if hasattr(self,"dateinput"):
			result = re.match('(\d+).(\d+).(\d+)',self.dateinput["value"])
			if result:
				adatetime[0] = result.group(3)
				adatetime[1] = result.group(2)
				adatetime[2] = result.group(1)

		if adatetime[2]=="0000":
			return( { self.boneName: adatetime[3]+":"+adatetime[4]+":00" } )
		returnvalue = adatetime[0]+"."+adatetime[1]+"."+adatetime[2]+" "+adatetime[3]+":"+adatetime[4]+":00"
		return( { self.boneName: returnvalue } )

	def serializeForDocument(self):
		return( self.serialize( ) )

def CheckForDateBone(  modulName, boneName, skelStucture ):
	return( skelStucture[boneName]["type"]=="date" )

#Register this Bone in the global queue
editBoneSelector.insert( 3, CheckForDateBone, DateEditBone)
viewDelegateSelector.insert( 3, CheckForDateBone, DateViewBoneDelegate)
