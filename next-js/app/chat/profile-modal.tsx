"use client"

import { useRouter } from 'next/navigation';
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { User, Settings, FileText, CreditCard, Bell, Shield, LogOut } from 'lucide-react'

interface ProfileModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function ProfileModal({ isOpen, onClose }: ProfileModalProps) {
  const profileMenuItems = [
    {
      icon: User,
      title: "내 정보 변경",
      description: "이름, 연락처 등 개인정보 수정",
      onClick: () => console.log("내 정보 변경")
    },
    {
      icon: FileText,
      title: "가입 내역",
      description: "보험 가입 및 상담 이력 확인",
      onClick: () => console.log("가입 내역")
    },
    {
      icon: CreditCard,
      title: "계정 정보",
      description: "로그인 정보 및 보안 설정",
      onClick: () => console.log("계정 정보")
    },
    {
      icon: Bell,
      title: "알림 설정",
      description: "푸시 알림 및 이메일 수신 설정",
      onClick: () => console.log("알림 설정")
    },
    {
      icon: Shield,
      title: "개인정보 보호",
      description: "개인정보 처리방침 및 약관",
      onClick: () => console.log("개인정보 보호")
    },
    {
      icon: Settings,
      title: "설정",
      description: "앱 설정 및 기타 옵션",
      onClick: () => console.log("설정")
    }
  ]
  const router = useRouter();
  const handleLogout = async () => {
  await fetch("/api/logout");
  router.push("/");
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl">내 정보</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 사용자 정보 */}
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-3">
              <User className="h-8 w-8 text-white" />
            </div>
            <h3 className="font-semibold text-lg">홍길동</h3>
            <p className="text-sm text-gray-600">hong@example.com</p>
          </div>

          <Separator />

          {/* 메뉴 항목들 */}
          <div className="space-y-2">
            {profileMenuItems.map((item, index) => (
              <Button
                key={index}
                variant="ghost"
                className="w-full justify-start h-auto p-4 hover:bg-orange-50"
                onClick={item.onClick}
              >
                <item.icon className="mr-3 h-5 w-5 text-gray-600" />
                <div className="text-left">
                  <div className="font-medium">{item.title}</div>
                  <div className="text-xs text-gray-500">{item.description}</div>
                </div>
              </Button>
            ))}
          </div>

          <Separator />

          {/* 로그아웃 */}
          <Button
            variant="ghost"
            className="w-full justify-start text-red-600 hover:bg-red-50 hover:text-red-700"
            onClick={handleLogout}
          >
            <LogOut className="mr-3 h-5 w-5" />
            로그아웃
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
