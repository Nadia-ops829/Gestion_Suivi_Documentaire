from rest_framework import serializers
from .models import BEX, BEXItem, Conteneur, ADI, CCPQ, DocumentTransit

class BEXItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BEXItem
        fields = ['id', 'numero_conteneur', 'designation_produit', 'quantite', 'facture_fcfa']

class ADISerializer(serializers.ModelSerializer):
    class Meta:
        model = ADI
        fields = '__all__'

class CCPQSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCPQ
        fields = '__all__'

class DocumentTransitSerializer(serializers.ModelSerializer):
    agent_createur_name = serializers.ReadOnlyField(source='agent_createur.username')
    class Meta:
        model = DocumentTransit
        fields = '__all__'

class ConteneurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conteneur
        fields = '__all__'

class BEXSerializer(serializers.ModelSerializer):
    items = BEXItemSerializer(many=True, required=False)
    agent_createur_name = serializers.ReadOnlyField(source='agent_createur.username')

    class Meta:
        model = BEX
        fields = '__all__'

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        bex = BEX.objects.create(**validated_data)
        for item_data in items_data:
            BEXItem.objects.create(bex=bex, **item_data)
            Conteneur.objects.get_or_create(bex=bex, numero_conteneur=item_data.get('numero_conteneur'))
        return bex

class BEXDossierCompletSerializer(serializers.ModelSerializer):
    items = BEXItemSerializer(many=True, read_only=True)
    conteneurs = ConteneurSerializer(many=True, read_only=True)
    adis = ADISerializer(many=True, read_only=True)
    ccpqs = CCPQSerializer(many=True, read_only=True)
    documents = DocumentTransitSerializer(many=True, read_only=True)
    
    class Meta:
        model = BEX
        fields = '__all__'
