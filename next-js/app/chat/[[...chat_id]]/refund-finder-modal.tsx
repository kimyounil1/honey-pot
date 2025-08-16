"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { UploadCloud, SearchCheck } from 'lucide-react'
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea" // Textarea 임포트

interface RefundFinderModalProps {
  isOpen: boolean
  onClose: () => void
  onAnalyze: (medicalCertificate: File | null, detailedBill: File | null, textInput?: string) => void // textInput 추가
}

export default function RefundFinderModal({ isOpen, onClose, onAnalyze }: RefundFinderModalProps) {
  const [medicalCertificate, setMedicalCertificate] = useState<File | null>(null)
  const [detailedBill, setDetailedBill] = useState<File | null>(null)
  const [textInput, setTextInput] = useState("") // 텍스트 입력 상태 추가

  const handleMedicalCertificateChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setMedicalCertificate(event.target.files[0])
    }
  }

  const handleDetailedBillChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setDetailedBill(event.target.files[0])
    }
  }

  const handleAnalyze = () => {
    if (textInput.trim() || (medicalCertificate && detailedBill)) {
      onAnalyze(medicalCertificate, detailedBill, textInput)
      onClose()
      setMedicalCertificate(null)
      setDetailedBill(null)
      setTextInput("")
    }
  }

  const handleClose = () => {
    onClose()
    setMedicalCertificate(null)
    setDetailedBill(null)
    setTextInput("")
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-xl">환급금 찾기</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* 메인 채팅 입력창 */}
          <div className="space-y-2">
            <Label htmlFor="refund-text-input">밑에 예시처럼 입력 해주세요</Label>
            <Textarea // Textarea로 변경
              id="refund-text-input"
              placeholder="예시 : 2025년 8월 9일 OO병명(질병, 상해 등)으로 어떤 진료를 받았고 OO과 병원에서 0원을 납부했음"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              rows={6} // 높이 조절
            />
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">더 자세히 알고 싶으면 첨부하세요</span>
            </div>
          </div>

          {/* 선택적 파일 업로드 */}
          <div className="space-y-4">
            {/* 진료확인서 업로드 */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center flex flex-col items-center justify-center bg-gray-50">
              <UploadCloud className="h-10 w-10 text-gray-400 mb-3" />
              <p className="text-gray-600 mb-2">질병 코드가 들어간 진료확인서</p>
              <Label htmlFor="medical-certificate-upload" className="cursor-pointer">
                <Button asChild variant="outline">
                  <span>파일 첨부하기</span>
                </Button>
                <Input id="medical-certificate-upload" type="file" className="hidden" onChange={handleMedicalCertificateChange} accept=".pdf,image/*" />
              </Label>
              {medicalCertificate && (
                <p className="mt-2 text-sm text-gray-700">{medicalCertificate.name}</p>
              )}
            </div>

            {/* 진료비 세부 내역서 업로드 */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center flex flex-col items-center justify-center bg-gray-50">
              <UploadCloud className="h-10 w-10 text-gray-400 mb-3" />
              <p className="text-gray-600 mb-2">진료비 세부 내역서</p>
              <Label htmlFor="detailed-bill-upload" className="cursor-pointer">
                <Button asChild variant="outline">
                  <span>파일 첨부하기</span>
                </Button>
                <Input id="detailed-bill-upload" type="file" className="hidden" onChange={handleDetailedBillChange} accept=".pdf,image/*" />
              </Label>
              {detailedBill && (
                <p className="mt-2 text-sm text-gray-700">{detailedBill.name}</p>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              onClick={handleAnalyze}
              disabled={!textInput.trim() && (!medicalCertificate || !detailedBill)}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
            >
              <SearchCheck className="mr-2 h-4 w-4" />첨부 안하고 채팅 시작
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
