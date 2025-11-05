class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    # bio = serializers.SerializerMethodField()
    nickname = serializers.SerializerMethodField()
    jdate_joined = serializers.SerializerMethodField()
    

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "role",
            "phone",
            "email",
            "must_change_password",
            "nickname",
            "avatar",
            "jdate_joined",
        ]
    def get_jdate_joined(self, obj):
        return j_convert_appoiment(obj.date_joined)

    def get_avatar(self, obj):
        if hasattr(obj, "manager_profile") and obj.manager_profile.avatar:
            request = self.context.get("request")
            avatar_url = obj.manager_profile.avatar.url
            if request:
                return request.build_absolute_uri(avatar_url)
            return avatar_url
        return None

    def get_nickname(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name if full_name else obj.username
    
    # def get_bio(self, obj):
    #     return obj.bio


# --------

class IsAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        بررسی اعتبار توکن و برگرداندن اطلاعات کاربر
          """
        user = request.user
        
        serializer = UserProfileSerializer(user)
        return Response(
            {
                "status": 200,
                "user": serializer.data
            },
            status=status.HTTP_200_OK
        )