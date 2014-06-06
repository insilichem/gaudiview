import chimera.extension

class GaudiViewEMO(chimera.extension.EMO):
	def name(self):
		return "GaudiView"
	def description(self):
		return "View results from Gaudi"
	def categories(self):
		return ['Surface/Binding Analysis']
	def activate(self):
		self.module('gui').browse()
		return None

emo = GaudiViewEMO(__file__)
chimera.extension.manager.registerExtension(emo)