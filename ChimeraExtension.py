import chimera.extension

class GaudiViewEMO(chimera.extension.EMO):
	def name(self):
		return "GAUDIView"
	def description(self):
		return "View results from GAUDI"
	def categories(self):
		return ['GAUDI']
	def activate(self):
		self.module('gui').browse()
		return None

emo = GaudiViewEMO(__file__)
chimera.extension.manager.registerExtension(emo)